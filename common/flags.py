from common.models import FeatureFlag


def is_enabled(name, user=None):
    """Is flag `name` on for `user`? Fails closed.

    - Unknown flag, or flag switched off: False for everyone.
    - audience "all": True for everyone, even anonymous callers.
    - audience "cohort" / "department": True only for a logged-in user who is
      in the named users / whose department is in the named departments.
    - Anything unrecognised: False.
    """
    flag = FeatureFlag.objects.filter(name=name).first()
    if flag is None or not flag.enabled:
        return False
    if flag.audience == FeatureFlag.AUDIENCE_ALL:
        return True
    if user is None or not user.is_authenticated:
        return False
    if flag.audience == FeatureFlag.AUDIENCE_COHORT:
        return flag.users.filter(pk=user.pk).exists()
    if flag.audience == FeatureFlag.AUDIENCE_DEPARTMENT:
        # A user with no profile raises RelatedObjectDoesNotExist, which is an
        # AttributeError, so getattr's default covers it.
        profile = getattr(user, "userprofile", None)
        department_id = getattr(profile, "department_id", None)
        return (
            department_id is not None
            and flag.departments.filter(pk=department_id).exists()
        )
    return False