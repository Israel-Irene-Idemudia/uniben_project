"""Personal board computation (Phase 4.3, BE-05.1; Phase 4.4 top entries,
BE-05.3): scoring, ties, windows, historical membership, scopes, exclusions,
paging."""
from datetime import timedelta

from django.test import TestCase

from accounts.models import AccountStatus
from leaderboards import boards
from leaderboards.boards import BoardWindow, personal_board, resolve_window
from seasons.models import Season
from xp.tests.helpers import make_admin

from .board_helpers import (
    adjust, earn, lagos, make_world, move, opening_balance, rule, season, spend, student,
)

LIFETIME = BoardWindow()


def ranking(page):
    return [(e.user_id, e.rank, e.xp) for e in page.entries]


class ScoringTests(TestCase):
    def setUp(self):
        self.w = make_world()
        self.admin = make_admin()

    def board(self, scope="university", unit=None, window=LIFETIME, **kw):
        return personal_board(scope=scope, unit_id=(unit or self.w["u1"]).pk, window=window, **kw)

    def test_only_awards_count(self):
        a = student("a", self.w["physics"])
        b = student("b", self.w["physics"])
        c = student("c", self.w["physics"])
        earn(a, 50, when=lagos(2026, 11, 3))
        earn(b, 30, when=lagos(2026, 11, 3))
        adjust(b, 500, when=lagos(2026, 11, 3), actor=self.admin)  # admin cannot move a rank
        opening_balance(c, 900, when=lagos(2026, 11, 3))  # legacy points are not earned XP
        page = self.board()
        self.assertEqual(ranking(page), [(a.pk, 1, 50), (b.pk, 2, 30)])
        self.assertEqual(page.total, 2)

    def test_spending_never_lowers_a_score(self):
        a = student("a", self.w["physics"])
        b = student("b", self.w["physics"])
        earn(a, 100, when=lagos(2026, 11, 3))
        earn(b, 60, when=lagos(2026, 11, 3))
        spend(a, 90, when=lagos(2026, 11, 4))  # balance 10, still 100 on the board
        self.assertEqual(ranking(self.board()), [(a.pk, 1, 100), (b.pk, 2, 60)])

    def test_capped_zero_awards_do_not_put_a_student_on_the_board(self):
        rule("capped", amount=5, daily_cap=5)
        a = student("a", self.w["physics"])
        z = student("z", self.w["physics"])
        earn(a, 5, when=lagos(2026, 11, 3, 9), action_code="capped")
        earn(z, 5, when=lagos(2026, 11, 3, 9), action_code="capped")
        earn(z, 5, when=lagos(2026, 11, 3, 10), action_code="capped")  # capped: a 0 row
        page = self.board()
        self.assertEqual(ranking(page), [(a.pk, 1, 5), (z.pk, 1, 5)])

    def test_students_with_no_xp_are_not_ranked(self):
        student("idle", self.w["physics"])
        self.assertEqual(self.board().total, 0)


class TieTests(TestCase):
    def test_ties_share_a_rank_and_order_is_stable(self):
        w = make_world()
        users = [student(f"s{i}", w["physics"]) for i in range(4)]
        for user, xp in zip(users, (40, 70, 40, 70)):
            earn(user, xp, when=lagos(2026, 11, 3))
        first = personal_board(scope="department", unit_id=w["physics"].pk, window=LIFETIME)
        expected = [
            (users[1].pk, 1, 70), (users[3].pk, 1, 70), (users[0].pk, 3, 40), (users[2].pk, 3, 40),
        ]
        self.assertEqual(ranking(first), expected)  # competition ranking, id tie-break
        self.assertEqual([e.position for e in first.entries], [1, 2, 3, 4])
        again = personal_board(scope="department", unit_id=w["physics"].pk, window=LIFETIME)
        self.assertEqual(ranking(again), expected)


class WindowTests(TestCase):
    def setUp(self):
        self.w = make_world()
        self.start, self.end = lagos(2026, 11, 2), lagos(2026, 11, 9)
        self.week = season(Season.KIND_WEEK, self.start, self.end)
        self.window = resolve_window("week")

    def test_open_week_is_resolved_from_state(self):
        self.assertEqual(self.window.season, self.week)
        self.assertEqual((self.window.starts_at, self.window.ends_at), (self.start, self.end))

    def test_start_is_inclusive_end_is_exclusive(self):
        tiny = timedelta(microseconds=1)
        before = student("before", self.w["physics"])
        first = student("first", self.w["physics"])
        last = student("last", self.w["physics"])
        after = student("after", self.w["physics"])
        earn(before, 1, when=self.start - tiny)
        earn(first, 2, when=self.start)
        earn(last, 3, when=self.end - tiny)
        earn(after, 4, when=self.end)
        page = personal_board(scope="university", unit_id=self.w["u1"].pk, window=self.window)
        self.assertEqual({e.user_id for e in page.entries}, {first.pk, last.pk})
        lifetime = personal_board(scope="university", unit_id=self.w["u1"].pk, window=LIFETIME)
        self.assertEqual(lifetime.total, 4)

    def test_boundaries_are_utc_instants_not_lagos_dates(self):
        # 00:30 on 2 Nov in Lagos is 23:30 UTC on 1 Nov: inside the week,
        # because the window is the stored UTC instant, not a UTC date.
        s = student("s", self.w["physics"])
        earn(s, 5, when=lagos(2026, 11, 2, 0, 30))
        page = personal_board(scope="university", unit_id=self.w["u1"].pk, window=self.window)
        self.assertEqual(page.total, 1)

    def test_no_open_season_means_no_board(self):
        self.assertIsNone(resolve_window("season"))

    def test_closed_season_can_be_resolved_explicitly(self):
        closed = season(Season.KIND_TERM, lagos(2026, 1, 1), lagos(2026, 6, 1), state=Season.STATE_CLOSED)
        self.assertEqual(resolve_window("season", closed).season, closed)

    def test_wrong_kind_or_unknown_period_is_refused(self):
        with self.assertRaises(boards.BoardError):
            resolve_window("season", self.week)
        with self.assertRaises(boards.BoardError):
            resolve_window("lifetime", self.week)
        with self.assertRaises(boards.BoardError):
            resolve_window("month")


class MembershipAndScopeTests(TestCase):
    """Past XP stays with the department the student had at the time."""

    def setUp(self):
        self.w = make_world()

    def board(self, scope, unit, window=LIFETIME, **kw):
        return personal_board(scope=scope, unit_id=unit.pk, window=window, **kw)

    def test_department_change_does_not_move_past_xp(self):
        mover = student("mover", self.w["physics"])
        earn(mover, 40, when=lagos(2026, 11, 3))
        move(mover, self.w["history"], when=lagos(2026, 11, 5))
        earn(mover, 15, when=lagos(2026, 11, 6))
        self.assertEqual(ranking(self.board("department", self.w["physics"])), [(mover.pk, 1, 40)])
        self.assertEqual(ranking(self.board("department", self.w["history"])), [(mover.pk, 1, 15)])
        self.assertEqual(ranking(self.board("faculty", self.w["science"])), [(mover.pk, 1, 40)])
        self.assertEqual(ranking(self.board("faculty", self.w["arts"])), [(mover.pk, 1, 15)])
        # The whole university saw all of it, once.
        self.assertEqual(ranking(self.board("university", self.w["u1"])), [(mover.pk, 1, 55)])

    def test_xp_earned_with_no_department_counts_for_no_board(self):
        # Documented gap: no history row means no known membership.
        late = student("late")
        earn(late, 30, when=lagos(2026, 11, 3))
        move(late, self.w["physics"], when=lagos(2026, 11, 4))
        earn(late, 5, when=lagos(2026, 11, 5))
        self.assertEqual(ranking(self.board("university", self.w["u1"])), [(late.pk, 1, 5)])

    def test_universities_are_isolated(self):
        ours = student("ours", self.w["physics"])
        theirs = student("theirs", self.w["civil"])
        earn(ours, 10, when=lagos(2026, 11, 3))
        earn(theirs, 99, when=lagos(2026, 11, 3))
        self.assertEqual(ranking(self.board("university", self.w["u1"])), [(ours.pk, 1, 10)])
        self.assertEqual(ranking(self.board("university", self.w["u2"])), [(theirs.pk, 1, 99)])

    def test_faculty_board_spans_its_departments_only(self):
        p = student("p", self.w["physics"])
        c = student("c", self.w["chemistry"])
        h = student("h", self.w["history"])
        for user, xp in ((p, 10), (c, 20), (h, 30)):
            earn(user, xp, when=lagos(2026, 11, 3))
        self.assertEqual(ranking(self.board("faculty", self.w["science"])), [(c.pk, 1, 20), (p.pk, 2, 10)])

    def test_suspended_and_deleted_accounts_are_excluded_until_cleared(self):
        ok = student("ok", self.w["physics"])
        bad = student("bad", self.w["physics"])
        gone = student("gone", self.w["physics"])
        for user in (ok, bad, gone):
            earn(user, 10, when=lagos(2026, 11, 3))
        status = AccountStatus.objects.create(user=bad, state=AccountStatus.SUSPENDED)
        AccountStatus.objects.create(user=gone, state=AccountStatus.DELETED)
        self.assertEqual([e.user_id for e in self.board("university", self.w["u1"]).entries], [ok.pk])
        status.state = AccountStatus.ACTIVE
        status.save()
        self.assertEqual(
            [e.user_id for e in self.board("university", self.w["u1"]).entries], [ok.pk, bad.pk]
        )


class PagingTests(TestCase):
    def setUp(self):
        w = make_world()
        self.w = w
        self.uni = w["u1"]
        # 60 students, distinct scores: position n has 1000 - n XP.
        self.users = []
        for n in range(1, 61):
            user = student(f"p{n:02d}", w["physics"])
            earn(user, 1000 - n, when=lagos(2026, 11, 3))
            self.users.append(user)

    def page(self, **kw):
        return personal_board(scope="university", unit_id=self.uni.pk, window=LIFETIME, **kw)

    def test_rank_47_sees_self_neighbours_and_top_10_in_one_call(self):
        me = self.users[46]
        page = self.page(viewer_id=me.pk, limit=10, around=2)
        self.assertEqual([e.position for e in page.entries], list(range(1, 11)))
        self.assertEqual((page.me.rank, page.me.user_id, page.me.xp), (47, me.pk, 953))
        self.assertEqual([e.position for e in page.around_me], [45, 46, 47, 48, 49])
        self.assertEqual(page.total, 60)

    def test_offset_pages_and_past_the_end(self):
        page = self.page(offset=50, limit=20)
        self.assertEqual([e.position for e in page.entries], list(range(51, 61)))
        empty = self.page(offset=100, limit=10)
        self.assertEqual((empty.entries, empty.total), ([], 60))

    def test_around_is_clipped_at_the_top(self):
        page = self.page(viewer_id=self.users[0].pk, limit=1, around=3)
        self.assertEqual([e.position for e in page.around_me], [1, 2, 3, 4])

    def test_viewer_with_no_score_has_no_position(self):
        outsider = student("outsider")
        page = self.page(viewer_id=outsider.pk)
        self.assertIsNone(page.me)
        self.assertEqual(page.around_me, [])
        self.assertEqual(len(page.entries), 10)

    # Phase 4.4 (BE-05.3): top entries independent of the page.

    def test_top_is_independent_of_offset(self):
        me = self.users[46]
        page = self.page(viewer_id=me.pk, offset=40, limit=10, around=2, top=10)
        self.assertEqual([e.position for e in page.top], list(range(1, 11)))
        self.assertEqual([e.position for e in page.entries], list(range(41, 51)))
        self.assertEqual([e.position for e in page.around_me], [45, 46, 47, 48, 49])
        self.assertEqual(page.me.rank, 47)
        self.assertEqual(page.total, 60)

    def test_top_defaults_off_at_the_service_layer(self):
        page = self.page(offset=20, limit=5)
        self.assertEqual(page.top, [])
        self.assertEqual([e.position for e in page.entries], list(range(21, 26)))

    def test_top_larger_than_the_board_is_the_whole_board(self):
        page = self.page(top=100, limit=1)
        self.assertEqual([e.position for e in page.top], list(range(1, 61)))

    def test_past_the_end_with_top_still_reports_total(self):
        page = self.page(offset=100, limit=10, top=3)
        self.assertEqual(([e.position for e in page.top], page.entries, page.total), ([1, 2, 3], [], 60))

    def test_top_shares_ranks_on_ties(self):
        # Two more students level with position 1 (999 XP): ranks 1, 1, 1, 4.
        for name in ("tie_a", "tie_b"):
            earn(student(name, self.w["physics"]), 999, when=lagos(2026, 11, 3))
        page = self.page(top=4)
        self.assertEqual([e.rank for e in page.top], [1, 1, 1, 4])
        self.assertEqual([e.position for e in page.top], [1, 2, 3, 4])

    def test_empty_board_with_top(self):
        # Uni Two has no scored students.
        empty = personal_board(
            scope="university", unit_id=self.w["u2"].pk, window=LIFETIME, top=10, offset=5,
        )
        self.assertEqual((empty.top, empty.entries, empty.total), ([], [], 0))

