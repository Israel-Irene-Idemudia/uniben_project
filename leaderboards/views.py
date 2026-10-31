from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import UserProfile
from accounts.permissions import IsNotSuspended
from common.views import V1APIView
from core.models import Department, Faculty, University
from seasons.models import Season
from seasons.serializers import SeasonSerializer

from . import boards
from .serializers import ContributionRuleSetSerializer
from .services import get_active_rule_set


def _caller_university_id(user):
    # Read-only lookup: unlike accounts.v1_profile.profile_for, never creates
    # a profile from a GET.
    return (
        UserProfile.objects.filter(user=user)
        .values_list("faculty__university_id", flat=True)
        .first()
    )


class ScoringRulesView(V1APIView):
    """GET /api/v1/scoring-rules[?university_id=]

    The published contribution rule (BE-05.2, BE-05.6), for both clients to
    show verbatim. Defaults to the caller's own university; falls back to
    the global rule; `rule_set` is null when nothing is published. Drafts
    and retired sets are never returned.

    Authenticated, read-only. Not IsNotSuspended: reading the rules is not a
    competitive action (same reasoning as /seasons/current).
    """

    def get(self, request):
        raw = request.query_params.get("university_id")
        if raw:
            if not raw.isdigit():
                raise ValidationError({"university_id": ["Must be a number."]})
            university = University.objects.filter(pk=int(raw), is_active=True).first()
            if university is None:
                raise NotFound("University not found.")
            university_id = university.pk
        else:
            university_id = _caller_university_id(request.user)
        rule_set = get_active_rule_set(university_id)
        return Response(
            {"rule_set": ContributionRuleSetSerializer(rule_set).data if rule_set is not None else None}
        )


# Paging bounds for the personal board (API-03). Small on purpose: the
# board is a screen, not an export.
DEFAULT_LIMIT, MAX_LIMIT = 10, 100
DEFAULT_AROUND, MAX_AROUND = 2, 10
# Phase 4.4 (BE-05.3): the top entries ride along on every response, so a
# client paged to rank 47 still gets the top 10. 10 = the SRS acceptance case.
DEFAULT_TOP, MAX_TOP = 10, 100
MAX_OFFSET = 100_000


def _int_param(request, name, *, default, minimum, maximum):
    raw = request.query_params.get(name)
    if raw is None or raw == "":
        return default
    if not raw.isdigit() or not (minimum <= int(raw) <= maximum):
        raise ValidationError({name: [f"Must be a whole number from {minimum} to {maximum}."]})
    return int(raw)


def _optional_id(request, name):
    raw = request.query_params.get(name)
    if not raw:
        return None
    if not raw.isdigit():
        raise ValidationError({name: ["Must be a number."]})
    return int(raw)


def _ref(obj):
    return None if obj is None else {"id": obj.id, "name": obj.name, "code": getattr(obj, "code", None)}


def _entry_data(entry, viewer_id):
    return {
        "rank": entry.rank,
        "position": entry.position,
        # Same fields as the public profile: no private data on a board.
        "user": {"id": entry.user_id, "username": entry.username, "display_name": entry.display_name},
        "xp": entry.xp,
        "is_me": entry.user_id == viewer_id,
    }


class PersonalLeaderboardView(V1APIView):
    """GET /api/v1/leaderboards/{scope}/{period}

    scope: department | faculty | university. period: lifetime | week | season.
    Query: offset (0), limit (10, max 100), around (2, max 10), top (10, 0..100),
    department_id / faculty_id (another unit in the caller's own university),
    season_id (an open or closed season of the period's kind).

    BE-05.3 (Phase 4.4): one response carries `top` (positions 1..top, not
    affected by offset), the `entries` page, `me` and `around_me`, all from
    a single board query.

    Ranks and XP come only from the ledger (D7); nothing here reads a client
    number. Isolation: every unit is looked up inside the caller's own
    university, so another university's board is a 404, the same as a
    unit that does not exist.

    IsNotSuspended: boards are competitive (BE-01.5). Suspended students
    are also left off every board, and quarantined awards are left out of
    every score (BE-05.5, Phase 4.5; both in leaderboards.boards).
    """

    permission_classes = [IsAuthenticated, IsNotSuspended]

    def get(self, request, scope, period):
        if scope not in boards.SCOPES or period not in boards.PERIODS:
            raise NotFound("Unknown leaderboard.")
        offset = _int_param(request, "offset", default=0, minimum=0, maximum=MAX_OFFSET)
        limit = _int_param(request, "limit", default=DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)
        around = _int_param(request, "around", default=DEFAULT_AROUND, minimum=0, maximum=MAX_AROUND)
        top = _int_param(request, "top", default=DEFAULT_TOP, minimum=0, maximum=MAX_TOP)

        profile = (
            UserProfile.objects.filter(user=request.user)
            .select_related("faculty__university", "department__faculty__university")
            .first()
        )  # read-only: a GET never creates a profile
        university = _caller_university(profile)
        unit = _board_unit(request, scope, profile, university)
        window = _board_window(request, period)

        page = None
        if unit is not None and window is not None:
            page = boards.personal_board(
                scope=scope, unit_id=unit.pk, window=window, viewer_id=request.user.pk,
                offset=offset, limit=limit, around=around, top=top,
            )
        viewer = request.user.pk
        return Response(
            {
                "scope": scope,
                "period": period,
                "university": _ref(university),
                "unit": _ref(unit),
                "season": SeasonSerializer(window.season).data if window and window.season else None,
                "total": page.total if page else 0,
                "offset": offset,
                "limit": limit,
                "next_offset": offset + limit if page and offset + limit < page.total else None,
                "me": _entry_data(page.me, viewer) if page and page.me else None,
                "top": [_entry_data(e, viewer) for e in page.top] if page else [],
                "entries": [_entry_data(e, viewer) for e in page.entries] if page else [],
                "around_me": [_entry_data(e, viewer) for e in page.around_me] if page else [],
            }
        )



def _caller_university(profile):
    """The caller's university, through their faculty (D-16). None until set."""
    if profile is None:
        return None
    faculty = profile.faculty or (profile.department.faculty if profile.department else None)
    return faculty.university if faculty is not None else None


def _board_unit(request, scope, profile, university):
    """The board's unit, always inside the caller's university. None when the
    caller has not set one yet (the app shows 'complete your profile')."""
    if scope == boards.SCOPE_UNIVERSITY:
        return university
    param = "department_id" if scope == boards.SCOPE_DEPARTMENT else "faculty_id"
    requested = _optional_id(request, param)
    if requested is None:
        if profile is None:
            return None
        return profile.department if scope == boards.SCOPE_DEPARTMENT else profile.faculty
    if university is None:
        raise NotFound("Leaderboard not found.")
    # Isolation: the lookup itself is scoped to the caller's university, so
    # another university's unit and a missing unit are indistinguishable.
    if scope == boards.SCOPE_DEPARTMENT:
        unit = Department.objects.filter(pk=requested, faculty__university=university).first()
    else:
        unit = Faculty.objects.filter(pk=requested, university=university).first()
    if unit is None:
        raise NotFound("Leaderboard not found.")
    return unit


def _board_window(request, period):
    season_id = _optional_id(request, "season_id")
    if season_id is None:
        return boards.resolve_window(period)
    if period == boards.PERIOD_LIFETIME:
        raise ValidationError({"season_id": ["A lifetime board has no season."]})
    # Scheduled seasons are not shown (same rule as /seasons/current).
    season = Season.objects.filter(
        pk=season_id,
        kind=boards.SEASON_KIND_FOR_PERIOD[period],
        state__in=[Season.STATE_OPEN, Season.STATE_CLOSED],
    ).first()
    if season is None:
        raise NotFound("Season not found.")
    return boards.resolve_window(period, season)

