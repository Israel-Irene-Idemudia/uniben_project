"""Phase 4.5 (BE-05.5, D-22): quarantined awards are excluded from every
personal board; unquarantined awards keep counting; ranks, ties, top,
around_me and me all follow; account-state exclusions and university
isolation are unchanged; the ledger row itself is untouched."""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from accounts.account_state import set_account_state
from accounts.models import AccountStatus
from leaderboards.boards import BoardWindow, personal_board, resolve_window
from seasons.models import Season
from xp.models import XPLedgerEntry, XPQuarantine
from xp.quarantine import quarantine_award
from xp.services import get_balance, get_lifetime_xp
from xp.tests.helpers import make_admin

from .board_helpers import earn, lagos, make_world, season, student

LIFETIME = BoardWindow()
BASE = "/api/v1/leaderboards"


def ranking(page):
    return [(e.user_id, e.rank, e.xp) for e in page.entries]


class QuarantineExclusionTests(TestCase):
    def setUp(self):
        self.w = make_world()
        self.admin = make_admin()

    def board(self, scope="university", unit=None, window=LIFETIME, **kw):
        return personal_board(scope=scope, unit_id=(unit or self.w["u1"]).pk, window=window, **kw)

    def quarantine(self, entry):
        return quarantine_award(entry, actor=self.admin, reason="Suspected cheating")

    def test_quarantined_award_is_excluded_other_awards_still_count(self):
        a = student("a", self.w["physics"])
        b = student("b", self.w["physics"])
        earn(a, 30, when=lagos(2026, 11, 3))
        bad = earn(a, 100, when=lagos(2026, 11, 3, 12))
        earn(b, 50, when=lagos(2026, 11, 3))
        self.assertEqual(ranking(self.board()), [(a.pk, 1, 130), (b.pk, 2, 50)])
        self.quarantine(bad)
        self.assertEqual(ranking(self.board()), [(b.pk, 1, 50), (a.pk, 2, 30)])

    def test_student_whose_only_award_is_quarantined_leaves_the_board(self):
        a = student("a", self.w["physics"])
        b = student("b", self.w["physics"])
        only = earn(a, 80, when=lagos(2026, 11, 3))
        earn(b, 20, when=lagos(2026, 11, 3))
        self.quarantine(only)
        page = self.board(viewer_id=a.pk, top=10)
        self.assertEqual(ranking(page), [(b.pk, 1, 20)])
        self.assertEqual(page.total, 1)
        self.assertIsNone(page.me)
        self.assertEqual(page.around_me, [])

    def test_quarantine_reranks_with_competition_ties(self):
        a, b, c, d = [student(f"s{i}", self.w["physics"]) for i in range(4)]
        earn(a, 50, when=lagos(2026, 11, 3))
        earn(b, 70, when=lagos(2026, 11, 3))
        earn(c, 70, when=lagos(2026, 11, 3))
        bonus = earn(c, 30, when=lagos(2026, 11, 4))
        earn(d, 40, when=lagos(2026, 11, 3))
        self.assertEqual(
            ranking(self.board()), [(c.pk, 1, 100), (b.pk, 2, 70), (a.pk, 3, 50), (d.pk, 4, 40)]
        )
        self.quarantine(bonus)
        page = self.board()
        # b and c now tie on 70: ranks 1, 1, 3, 4; tie order = user id.
        self.assertEqual(ranking(page), [(b.pk, 1, 70), (c.pk, 1, 70), (a.pk, 3, 50), (d.pk, 4, 40)])
        self.assertEqual([e.position for e in page.entries], [1, 2, 3, 4])
        self.assertEqual(ranking(self.board()), ranking(page))  # deterministic

    def test_exclusion_applies_to_department_faculty_and_university(self):
        p = student("p", self.w["physics"])
        h = student("h", self.w["history"])
        bad = earn(p, 60, when=lagos(2026, 11, 3))
        earn(p, 5, when=lagos(2026, 11, 3, 12))
        earn(h, 10, when=lagos(2026, 11, 3))
        self.quarantine(bad)
        self.assertEqual(ranking(self.board("department", self.w["physics"])), [(p.pk, 1, 5)])
        self.assertEqual(ranking(self.board("faculty", self.w["science"])), [(p.pk, 1, 5)])
        self.assertEqual(ranking(self.board()), [(h.pk, 1, 10), (p.pk, 2, 5)])

    def test_exclusion_applies_to_seasonal_windows(self):
        week = season(Season.KIND_WEEK, lagos(2026, 11, 2), lagos(2026, 11, 9))
        s = student("s", self.w["physics"])
        earn(s, 7, when=lagos(2026, 10, 20))  # before the week: lifetime only
        bad = earn(s, 40, when=lagos(2026, 11, 3))  # inside the week
        self.quarantine(bad)
        window = resolve_window("week")
        self.assertEqual(window.season, week)
        self.assertEqual(self.board(window=window).total, 0)
        self.assertEqual(ranking(self.board()), [(s.pk, 1, 7)])

    def test_unquarantined_awards_are_unaffected(self):
        a = student("a", self.w["physics"])
        b = student("b", self.w["physics"])
        earn(a, 10, when=lagos(2026, 11, 3))
        earn(b, 20, when=lagos(2026, 11, 3))
        other = earn(student("x", self.w["chemistry"]), 99, when=lagos(2026, 11, 3))
        before = ranking(self.board("department", self.w["physics"]))
        self.quarantine(other)
        self.assertEqual(ranking(self.board("department", self.w["physics"])), before)

    def test_a_closed_quarantine_counts_again(self):
        # Forward compatibility with Phase 5.8: scoring excludes only OPEN
        # cases, so a cleared row (written by 5.8's review) needs no board change.
        a = student("a", self.w["physics"])
        entry = earn(a, 25, when=lagos(2026, 11, 3))
        XPQuarantine.objects.create(
            entry=entry, state=XPQuarantine.STATE_CLEARED, reason="Reviewed: fine", flagged_by=self.admin,
        )
        self.assertEqual(ranking(self.board()), [(a.pk, 1, 25)])

    def test_suspended_and_deleted_stay_excluded_alongside_quarantine(self):
        ok = student("ok", self.w["physics"])
        held = student("held", self.w["physics"])
        bad = student("bad", self.w["physics"])
        gone = student("gone", self.w["physics"])
        earn(ok, 10, when=lagos(2026, 11, 3))
        flagged = earn(held, 50, when=lagos(2026, 11, 3))
        earn(bad, 40, when=lagos(2026, 11, 3))
        earn(gone, 30, when=lagos(2026, 11, 3))
        self.quarantine(flagged)
        set_account_state(bad, AccountStatus.SUSPENDED, actor=self.admin, reason="Abuse report")
        AccountStatus.objects.create(user=gone, state=AccountStatus.DELETED)
        self.assertEqual(ranking(self.board()), [(ok.pk, 1, 10)])
        # Reinstating the account brings its clean XP back; the quarantine still holds.
        set_account_state(bad, AccountStatus.ACTIVE, actor=self.admin, reason="Appeal accepted")
        self.assertEqual(ranking(self.board()), [(bad.pk, 1, 40), (ok.pk, 2, 10)])

    def test_universities_stay_isolated(self):
        ours = student("ours", self.w["physics"])
        theirs = student("theirs", self.w["civil"])
        mine = earn(ours, 10, when=lagos(2026, 11, 3))
        earn(theirs, 10, when=lagos(2026, 11, 3))
        self.quarantine(mine)
        self.assertEqual(self.board(unit=self.w["u1"]).total, 0)
        self.assertEqual(ranking(self.board(unit=self.w["u2"])), [(theirs.pk, 1, 10)])

    def test_ledger_row_is_untouched_and_balance_unchanged(self):
        a = student("a", self.w["physics"])
        entry = earn(a, 45, when=lagos(2026, 11, 3))
        snapshot = XPLedgerEntry.objects.filter(pk=entry.pk).values().get()
        rows = XPLedgerEntry.objects.count()
        balance, lifetime = get_balance(a), get_lifetime_xp(a)
        self.quarantine(entry)
        self.assertEqual(XPLedgerEntry.objects.filter(pk=entry.pk).values().get(), snapshot)
        self.assertEqual(XPLedgerEntry.objects.count(), rows)  # nothing appended either
        # D-2 unchanged: quarantine is a board exclusion only.
        self.assertEqual((get_balance(a), get_lifetime_xp(a)), (balance, lifetime))
        self.assertEqual(self.board().total, 0)



class QuarantineEndpointTests(TestCase):
    """The same exclusion through GET /leaderboards: top, entries, me and
    around_me stay consistent with each other and still come from ONE query."""

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.admin = make_admin()
        cls.users, cls.awards = [], []
        # 60 students, position n has 1000 - n XP (same shape as Phase 4.4).
        for n in range(1, 61):
            user = student(f"s{n:02d}", cls.w["physics"])
            cls.awards.append(earn(user, 1000 - n, when=lagos(2026, 11, 3)))
            cls.users.append(user)
        cls.foreign = student("foreign", cls.w["civil"])
        cls.foreign_award = earn(cls.foreign, 5000, when=lagos(2026, 11, 3))
        cls.me = cls.users[46]  # rank 47, 953 XP

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.me)

    def get(self, path="university/lifetime", **params):
        r = self.client.get(f"{BASE}/{path}", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def quarantine(self, entry):
        quarantine_award(entry, actor=self.admin, reason="Impossible completion time")

    def test_top_around_me_and_me_move_up_together(self):
        self.quarantine(self.awards[0])
        self.quarantine(self.awards[1])
        body = self.get(offset=40, limit=10)
        self.assertEqual(body["total"], 58)
        self.assertEqual((body["me"]["rank"], body["me"]["position"], body["me"]["xp"]), (45, 45, 953))
        self.assertEqual(body["top"][0]["user"]["id"], self.users[2].id)
        self.assertEqual([e["position"] for e in body["top"]], list(range(1, 11)))
        self.assertEqual([e["position"] for e in body["entries"]], list(range(41, 51)))
        self.assertEqual([e["position"] for e in body["around_me"]], [43, 44, 45, 46, 47])
        excluded = {self.users[0].id, self.users[1].id}
        for name in ("top", "entries", "around_me"):
            self.assertFalse(excluded & {e["user"]["id"] for e in body[name]}, name)
        # One student, one answer: the same rank/position/xp in every list.
        seen = {}
        for name in ("top", "entries", "around_me"):
            for e in body[name]:
                expected = seen.setdefault(e["user"]["id"], (e["rank"], e["position"], e["xp"]))
                self.assertEqual(expected, (e["rank"], e["position"], e["xp"]))
        self.assertEqual(seen[self.me.id], (45, 45, 953))

    def test_viewer_whose_award_is_quarantined_has_no_position(self):
        self.quarantine(self.awards[46])
        body = self.get()
        self.assertIsNone(body["me"])
        self.assertEqual(body["around_me"], [])
        self.assertEqual(body["total"], 59)
        self.assertEqual([e["position"] for e in body["top"]], list(range(1, 11)))

    def test_quarantine_can_create_a_tie_in_top(self):
        # s01 earns a second 998; quarantining its first 999 leaves s01 on
        # 998, level with s02: ranks 1, 1, 3, s01 first by user id.
        earn(self.users[0], 998, when=lagos(2026, 11, 4))
        self.quarantine(self.awards[0])
        body = self.get(top=3)
        self.assertEqual(
            [(e["user"]["id"], e["rank"], e["xp"]) for e in body["top"]],
            [(self.users[0].id, 1, 998), (self.users[1].id, 1, 998), (self.users[2].id, 3, 997)],
        )

    def test_still_one_board_query(self):
        self.quarantine(self.awards[0])
        with CaptureQueriesContext(connection) as ctx:
            self.get(offset=40, limit=10, top=10)
        self.assertEqual(len([q for q in ctx.captured_queries if "RANK() OVER" in q["sql"]]), 1)

    def test_other_university_quarantine_does_not_leak(self):
        self.quarantine(self.foreign_award)
        body = self.get(top=100)
        self.assertEqual(body["total"], 60)
        self.assertNotIn(self.foreign.id, {e["user"]["id"] for e in body["top"]})

