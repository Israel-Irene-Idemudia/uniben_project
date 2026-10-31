"""Small helpers shared by the xp and rewards tests."""
from django.contrib.auth import get_user_model

from accounts.models import UserProfile
from xp.services import adjust_xp

User = get_user_model()
_counter = {"n": 0}


def make_student(username="student", points=0):
    """A student with a profile and `points` already in the ledger."""
    user = User.objects.create_user(username=username, password="pass12345", email=f"{username}@test.com")
    UserProfile.objects.get_or_create(user=user)
    if points:
        give_points(user, points)
    return user


def make_admin(username="boss"):
    return User.objects.create_superuser(username=username, password="pass12345", email=f"{username}@test.com")


def give_points(user, amount):
    """Put points on a student the legitimate way: an audited admin adjustment."""
    _counter["n"] += 1
    admin_user = User.objects.filter(is_superuser=True).first() or make_admin("helper_admin")
    return adjust_xp(
        user,
        amount=amount,
        reason="test setup",
        actor=admin_user,
        idempotency_key=f"test-give:{_counter['n']}",
    )
