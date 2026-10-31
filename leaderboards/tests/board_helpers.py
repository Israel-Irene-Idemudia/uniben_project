"""Fixtures for the personal leaderboard tests (Phase 4.3).

Ledger rows are immutable and created_at is auto_now_add, so the only honest
way to place XP at a given instant is to run the real service with the clock
patched. Department history is written by the real profile-save signal under
the same patched clock, so membership dates are exactly what production
would record.
"""
from datetime import datetime
from itertools import count
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model

from accounts.models import UserProfile
from core.models import Department, Faculty, University
from seasons.models import Season
from xp.models import XPLedgerEntry, XPRule
from xp.services import adjust_xp, award_xp, spend_points

User = get_user_model()
LAGOS = ZoneInfo("Africa/Lagos")
UTC = ZoneInfo("UTC")
_seq = count(1)

# A fixed instant long before any test week: default "joined" time.
EARLY = datetime(2026, 1, 1, tzinfo=LAGOS)


def lagos(*args):
    return datetime(*args, tzinfo=LAGOS)


def at(when):
    """Patch the clock used by auto_now_add and the services."""
    return mock.patch("django.utils.timezone.now", return_value=when)


def make_world():
    """Two universities. U1: Science (Physics, Chemistry), Arts (History).
    U2: Engineering (Civil)."""
    u1 = University.objects.create(name="Uni One", code="uni1")
    u2 = University.objects.create(name="Uni Two", code="uni2")
    science = Faculty.objects.create(name="Science", university=u1)
    arts = Faculty.objects.create(name="Arts", university=u1)
    eng = Faculty.objects.create(name="Engineering", university=u2)
    return {
        "u1": u1, "u2": u2, "science": science, "arts": arts, "eng": eng,
        "physics": Department.objects.create(name="Physics", faculty=science),
        "chemistry": Department.objects.create(name="Chemistry", faculty=science),
        "history": Department.objects.create(name="History", faculty=arts),
        "civil": Department.objects.create(name="Civil", faculty=eng),
    }


def student(username, department=None, *, since=EARLY, first_name="", last_name=""):
    """A student (cheap: no password hashing) placed in `department` from
    `since`, through the real profile signal."""
    with at(since):
        user = User.objects.create(username=username, first_name=first_name, last_name=last_name)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if department is not None:
            move(user, department, when=since)
    return user


def move(user, department, *, when):
    """Change department at `when` (history closes the old row, opens a new one)."""
    with at(when):
        profile = UserProfile.objects.get(user=user)
        profile.department = department
        profile.faculty = department.faculty
        profile.save()


def rule(action_code="test_action", amount=10, daily_cap=None):
    return XPRule.objects.get_or_create(
        action_code=action_code, defaults={"amount": amount, "daily_cap": daily_cap}
    )[0]


def earn(user, amount, *, when, action_code="test_action"):
    """A real award of `amount` XP at `when`."""
    rule(action_code)
    with at(when):
        return award_xp(
            user, action_code=action_code, source_feature="test",
            source_record_id=f"r{next(_seq)}", amount=amount,
        ).entry


def spend(user, cost, *, when):
    with at(when):
        return spend_points(
            user, cost=cost, reason_code="reward", source_feature="test",
            idempotency_key=f"spend:{next(_seq)}",
        )


def adjust(user, amount, *, when, actor):
    with at(when):
        return adjust_xp(user, amount=amount, reason="test", actor=actor, idempotency_key=f"adj:{next(_seq)}")


def opening_balance(user, amount, *, when):
    with at(when):
        return XPLedgerEntry.objects.create(
            user=user, amount=amount, kind=XPLedgerEntry.KIND_OPENING_BALANCE,
            reason_code="opening_balance", source_feature="test", source_record_id=str(user.pk),
            idempotency_key=f"opening_balance:{user.pk}",
        )


def season(kind, starts_at, ends_at, state=Season.STATE_OPEN, name="S"):
    # Direct create keeps the fixture small; seasons.services is tested in its own app.
    return Season.objects.create(name=name, kind=kind, starts_at=starts_at, ends_at=ends_at, state=state)
