"""Builds the /me and /me/progress payloads.

Public fields are what other students may one day see; private fields are for
the student and admins only (BE-02.3). Keep them in separate builders so a
future "view another student" endpoint can only ever call public_profile.
"""
from accounts.models import UserProfile


def profile_for(user):
    try:
        return UserProfile.objects.select_related("faculty", "department", "level").get(user=user)
    except UserProfile.DoesNotExist:
        # Old accounts may have no profile row: give them an empty one so the
        # app can show a "complete your profile" state instead of an error.
        UserProfile.objects.get_or_create(user=user)
        return UserProfile.objects.select_related("faculty", "department", "level").get(user=user)


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
    return {
        "id": user.id,
        "username": user.username,
        "display_name": full_name or user.username,
        "avatar": None,        # BE-03 (Javin): avatar config reference
        "xp_level": None,      # Phase 3: from the XP ledger
        "badges": [],          # Phase 8
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
    missing = missing_fields(profile)
    return {
        # Ledger-dependent fields stay null until Phase 3 (ledger) and
        # Phase 4 (ranks). Clients must treat null as "not available yet".
        "ledger_ready": False,
        "xp_total": None,
        "level": None,
        "xp_to_next_level": None,
        "personal_rank": None,
        "department_rank": None,
        "department": _ref(profile.department, with_code=True),
        "suggested_activities": [],
        "profile_complete": not missing,
        "missing_fields": missing,
    }