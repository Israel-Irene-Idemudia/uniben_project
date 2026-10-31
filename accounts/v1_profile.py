"""Builds the /me and /me/progress payloads.

Public fields are what other students may one day see; private fields are for
the student and admins only (BE-02.3). Keep them in separate builders so a
future "view another student" endpoint can only ever call public_profile.
"""
from accounts.models import UserProfile
from xp.services import get_balance, get_level


_PROFILE_RELATED = ("faculty", "faculty__university", "department", "level")


def profile_for(user):
    try:
        return UserProfile.objects.select_related(*_PROFILE_RELATED).get(user=user)
    except UserProfile.DoesNotExist:
        # Old accounts may have no profile row: give them an empty one so the
        # app can show a "complete your profile" state instead of an error.
        UserProfile.objects.get_or_create(user=user)
        return UserProfile.objects.select_related(*_PROFILE_RELATED).get(user=user)


def university_of(profile):
    """A student's university is reached through their faculty (no new
    column on student records). None until the faculty is set."""
    faculty = profile.faculty
    return faculty.university if faculty is not None else None


def _ref(obj, with_code=False):
    if obj is None:
        return None
    data = {"id": obj.id, "name": obj.name}
    if with_code:
        data["code"] = getattr(obj, "code", None)
    return data


def missing_fields(profile):
    return [f for f in ("faculty", "department", "level") if getattr(profile, f"{f}_id") is None]


def public_profile(profile):
    user = profile.user
    full_name = f"{user.first_name} {user.last_name}".strip()
    info = get_level(user)
    return {
        "id": user.id,
        "username": user.username,
        "display_name": full_name or user.username,
        "avatar": None,        # BE-03 (Javin): avatar config reference
        # XP level is public (it is earned, not spent). The spendable balance
        # is NOT public and lives in /me/progress and /me/xp only.
        "xp_level": info.level,
        "xp_level_title": info.title,
        "badges": [],          # Phase 8
        "university": _ref(university_of(profile), with_code=True),
        "faculty": _ref(profile.faculty, with_code=True),
        "department": _ref(profile.department, with_code=True),
        "academic_level": _ref(profile.level),  # core.Level: 100L, 200L...
    }


def private_profile(profile):
    user = profile.user
    return {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": profile.phone,
        "network": profile.network,
        "student_id": profile.student_id,
        "matric_number": profile.matric_number,
    }


def me_payload(profile):
    missing = missing_fields(profile)
    return {
        **public_profile(profile),
        "private": private_profile(profile),
        "profile_complete": not missing,
        "missing_fields": missing,
    }


def progress_payload(profile):
    """'How do I progress?' (BE-02.4).

    Every number comes from the XP ledger (xp.services), never from
    UserProfile.points, which is only a write-only mirror (see xp.services).
    xp_total is LIFETIME XP (D-2): spending never lowers it or the level.
    Ranks stay null until the Phase 4 boards exist; clients must treat null
    as "not available yet".
    """
    missing = missing_fields(profile)
    info = get_level(profile.user)
    return {
        "ledger_ready": True,
        "xp_total": info.lifetime_xp,
        "level": info.level,
        "level_title": info.title,
        "xp_to_next_level": info.xp_to_next_level,
        "balance": get_balance(profile.user),
        "personal_rank": None,
        "department_rank": None,
        "department": _ref(profile.department, with_code=True),
        "suggested_activities": [],
        "profile_complete": not missing,
        "missing_fields": missing,
    }