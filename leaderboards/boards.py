"""Personal leaderboards (Phase 4.3 computation, Phase 4.4 endpoint shape;
BE-05.1, BE-05.3).

Computed live in the database (D-5): one aggregate + window-function query
per request, no cache, no background job, no new tables.

DECISIONS (approved defaults, 30 Oct 2026; see DECISIONS.md D-5 and D-19):
- Score = SUM of `award` rows with amount > 0 earned in the period. Spends,
  admin adjustments and opening balances never count, so buying a reward
  never lowers a rank and an admin cannot move a student up a board.
  This is NOT the spendable balance and NOT lifetime XP (which includes
  adjustments and the opening balance).
- Membership is historical: an XP row counts for the department / faculty
  the student belonged to WHEN it was earned, read from
  StudentDepartmentHistory ([effective_from, effective_to)). A student who
  changed department mid-week appears on both boards with the XP earned in
  each. XP earned while the student had no history row (no department set)
  counts for no scoped board; that is a known gap, not guessed around.
- University = the university of the history row's faculty
  (Faculty.university). Boards never cross universities.
- Period windows are UTC, inclusive start, exclusive end: [starts_at, ends_at).
  Week and season come from seasons.Season (D-17); lifetime has no window.
- Ties share a rank (competition ranking: 1, 1, 3). Order inside a tie is
  user id ascending, so pages are stable between calls.
- Suspended and deleted accounts are excluded at read time (BE-05.5); their
  ledger rows are untouched.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db import connection

from accounts.models import AccountStatus, StudentDepartmentHistory
from core.models import Faculty
from seasons.models import Season
from xp.models import XPLedgerEntry

SCOPE_DEPARTMENT = "department"
SCOPE_FACULTY = "faculty"
SCOPE_UNIVERSITY = "university"
SCOPES = (SCOPE_DEPARTMENT, SCOPE_FACULTY, SCOPE_UNIVERSITY)

PERIOD_LIFETIME = "lifetime"
PERIOD_WEEK = "week"
PERIOD_SEASON = "season"
PERIODS = (PERIOD_LIFETIME, PERIOD_WEEK, PERIOD_SEASON)

# Which Season.kind backs each seasonal period.
SEASON_KIND_FOR_PERIOD = {PERIOD_WEEK: Season.KIND_WEEK, PERIOD_SEASON: Season.KIND_TERM}

# The only ledger rows that score (see module docstring).
SCORING_KIND = XPLedgerEntry.KIND_AWARD


@dataclass(frozen=True)
class BoardWindow:
    """[starts_at, ends_at) in UTC. Both None = lifetime."""

    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    season: Optional[Season] = None


@dataclass(frozen=True)
class BoardEntry:
    rank: int  # shared by ties
    position: int  # 1-based, unique, deterministic
    user_id: int
    username: str
    display_name: str
    xp: int


@dataclass(frozen=True)
class BoardPage:
    total: int
    entries: List[BoardEntry] = field(default_factory=list)  # offset/limit slice
    me: Optional[BoardEntry] = None
    around_me: List[BoardEntry] = field(default_factory=list)
    # Phase 4.4 (BE-05.3): positions 1..top, whatever offset the caller paged
    # to, so "your position" screens never need a second call for the top.
    top: List[BoardEntry] = field(default_factory=list)


class BoardError(Exception):
    """An expected refusal (unknown scope or period, wrong season kind)."""


def window_for_season(season: Season) -> BoardWindow:
    return BoardWindow(starts_at=season.starts_at, ends_at=season.ends_at, season=season)


def resolve_window(period: str, season: Optional[Season] = None) -> Optional[BoardWindow]:
    """The window for a period. Returns None when a seasonal period has no
    season to show (nothing open and none given): the board is empty, not
    an error. State decides "current", not the clock (seasons.services)."""
    if period not in PERIODS:
        raise BoardError(f"Unknown period '{period}'.")
    if period == PERIOD_LIFETIME:
        if season is not None:
            raise BoardError("A lifetime board has no season.")
        return BoardWindow()
    kind = SEASON_KIND_FOR_PERIOD[period]
    if season is None:
        season = Season.objects.filter(kind=kind, state=Season.STATE_OPEN).first()
        if season is None:
            return None
    elif season.kind != kind:
        raise BoardError(f"Season {season.pk} is not a {kind} season.")
    return window_for_season(season)


def _db_datetime(value: datetime):
    # Raw SQL bypasses the ORM's field adaptation. Without this, SQLite would
    # compare "...+00:00" strings against stored naive-UTC strings and get
    # the boundary wrong. On PostgreSQL this returns the aware value as is.
    return connection.ops.adapt_datetimefield_value(value)


def _scores_sql(scope: str, unit_id: int, window: BoardWindow) -> Tuple[str, list]:
    """SQL for (user_id, xp) on one board, plus its params."""
    if scope not in SCOPES:
        raise BoardError(f"Unknown scope '{scope}'.")
    ledger = XPLedgerEntry._meta.db_table
    history = StudentDepartmentHistory._meta.db_table
    faculty = Faculty._meta.db_table
    status = AccountStatus._meta.db_table

    # Historical membership: the history row in force when the XP was earned.
    # Half-open on both sides, matching sync_department_history, which closes
    # the old row and opens the new one at the same instant.
    joins = [
        f"JOIN {history} h ON h.user_id = l.user_id"
        " AND h.effective_from <= l.created_at"
        " AND (h.effective_to IS NULL OR l.created_at < h.effective_to)"
    ]
    where = ["l.kind = %s", "l.amount > 0"]
    params: list = [SCORING_KIND]

    if scope == SCOPE_DEPARTMENT:
        where.append("h.department_id = %s")
    elif scope == SCOPE_FACULTY:
        where.append("h.faculty_id = %s")
    else:
        joins.append(f"JOIN {faculty} f ON f.id = h.faculty_id")
        where.append("f.university_id = %s")
    params.append(unit_id)

    if window.starts_at is not None:
        where.append("l.created_at >= %s")
        params.append(_db_datetime(window.starts_at))
    if window.ends_at is not None:
        where.append("l.created_at < %s")
        params.append(_db_datetime(window.ends_at))

    # BE-05.5: no status row means active; any other state is off the board.
    where.append(
        f"NOT EXISTS (SELECT 1 FROM {status} s WHERE s.user_id = l.user_id AND s.state <> %s)"
    )
    params.append(AccountStatus.ACTIVE)

    sql = (
        f"SELECT l.user_id AS user_id, SUM(l.amount) AS xp FROM {ledger} l "
        + " ".join(joins)
        + " WHERE "
        + " AND ".join(where)
        + " GROUP BY l.user_id"
    )
    return sql, params


def build_board_sql(
    *, scope: str, unit_id: int, window: BoardWindow, viewer_id: Optional[int],
    offset: int, limit: int, around: int, top: int = 0,
) -> Tuple[str, list]:
    """One statement returning the top `top` positions, the requested page
    and the viewer's neighbours, already ranked (BE-05.3: one response, one
    board query). Public so the explain command shows exactly the query the
    endpoint runs. Every value is a bound parameter; only table names (from
    model metadata) are formatted in."""
    scores_sql, params = _scores_sql(scope, unit_id, window)
    user_table = get_user_model()._meta.db_table
    sql = (
        f"WITH scores AS ({scores_sql}), "
        "ranked AS ("
        "SELECT user_id, xp, "
        "RANK() OVER (ORDER BY xp DESC) AS rnk, "
        "ROW_NUMBER() OVER (ORDER BY xp DESC, user_id ASC) AS pos, "
        "COUNT(*) OVER () AS total "
        "FROM scores"
        "), "
        "mine AS (SELECT pos FROM ranked WHERE user_id = %s) "
        "SELECT r.user_id, r.xp, r.rnk, r.pos, r.total, u.username, u.first_name, u.last_name "
        f"FROM ranked r JOIN {user_table} u ON u.id = r.user_id "
        "WHERE r.pos <= %s "
        "OR (r.pos > %s AND r.pos <= %s) "
        "OR (r.pos >= (SELECT pos FROM mine) - %s AND r.pos <= (SELECT pos FROM mine) + %s) "
        "ORDER BY r.pos"
    )
    return sql, params + [viewer_id, top, offset, offset + limit, around, around]


def _entry(row) -> BoardEntry:
    user_id, xp, rank, position, _total, username, first, last = row
    full_name = f"{first or ''} {last or ''}".strip()
    return BoardEntry(
        rank=int(rank), position=int(position), user_id=user_id, username=username,
        display_name=full_name or username, xp=int(xp),
    )


def _count(scope: str, unit_id: int, window: BoardWindow) -> int:
    scores_sql, params = _scores_sql(scope, unit_id, window)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM ({scores_sql}) c", params)
        return int(cursor.fetchone()[0])


def personal_board(
    *, scope: str, unit_id: int, window: BoardWindow, viewer_id: Optional[int] = None,
    offset: int = 0, limit: int = 10, around: int = 2, top: int = 0,
) -> BoardPage:
    """A ranked personal board for one department, faculty or university.

    top: positions 1 .. top, independent of offset (0 = not requested).
    entries: positions offset+1 .. offset+limit (offset=0 is the top).
    me / around_me: the viewer and `around` students either side, or
    None / [] when the viewer has no score on this board.
    The three lists may overlap; each is complete on its own.
    """
    sql, params = build_board_sql(
        scope=scope, unit_id=unit_id, window=window, viewer_id=viewer_id,
        offset=offset, limit=limit, around=around, top=top,
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    if rows:
        total = int(rows[0][4])
    elif offset > 0 and top == 0:
        # Paged past the end with nothing else requested: still report the
        # size. With top > 0, no rows can only mean an empty board.
        total = _count(scope, unit_id, window)
    else:
        total = 0

    top_entries, entries, around_me, me = [], [], [], None
    my_pos = next((int(r[3]) for r in rows if r[0] == viewer_id), None)
    for row in rows:
        entry = _entry(row)
        if entry.position <= top:
            top_entries.append(entry)
        if offset < entry.position <= offset + limit:
            entries.append(entry)
        if my_pos is not None and abs(entry.position - my_pos) <= around:
            around_me.append(entry)
        if entry.user_id == viewer_id:
            me = entry
    return BoardPage(total=total, entries=entries, me=me, around_me=around_me, top=top_entries)

