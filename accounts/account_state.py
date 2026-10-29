"""Account states, suspension, and anonymising deletion (BE-01.5, BE-01.6, DATA-17)."""
from django.db import transaction

from accounts.models import (
    AccountDeletionRequest,
    AccountStatus,
    UserDebaterProgress,
    UserGpaEntry,
    UserNoteEntry,
    UserPreferences,
    UserProfile,
    UserTimetableEntry,
    UserTodoEntry,
)
from accounts.session_revocation import revoke_all_sessions
from common.services import log_audit
from core.models import ContactMessage

ACTIVE = AccountStatus.ACTIVE
SUSPENDED = AccountStatus.SUSPENDED
DELETED = AccountStatus.DELETED


def get_account_state(user):
    """'active' when the student has no status row."""
    return AccountStatus.objects.filter(user=user).values_list("state", flat=True).first() or ACTIVE


def set_account_state(user, state, *, actor, reason, request_id=None):
    """Suspend or reinstate an account. A reason is mandatory; the change is audited."""
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("A reason is required.")
    if state not in (ACTIVE, SUSPENDED):
        raise ValueError("State must be active or suspended.")
    with transaction.atomic():
        row, _ = AccountStatus.objects.get_or_create(user=user)
        row = AccountStatus.objects.select_for_update().get(pk=row.pk)
        if row.state == DELETED:
            raise ValueError("A deleted account cannot change state.")
        if row.state == state:
            return row
        before = row.state
        row.state = state
        row.reason = reason
        row.changed_by = actor
        row.save()
        log_audit(
            actor=actor,
            action="account.suspended" if state == SUSPENDED else "account.reinstated",
            target_type="User",
            target_id=user.pk,
            before={"state": before},
            after={"state": state},
            reason=reason,
            request_id=request_id,
        )
        return row


@transaction.atomic
def anonymise_user(user, *, actor, reason):
    """Delete a student's PERSONAL data but keep the account row.

    Why not delete the user: history, the XP ledger and the audit log point at
    the user and must survive (DATA-17). So the row stays, with no name, email,
    phone or matric number, no usable password, and logins disabled.
    Returns False if the account was already deleted.

    Known limits: older audit rows keep the username snapshot they were
    written with (they are immutable by design); redemption records are left
    as they are, to be decided with the Phase 3 reward rules (D-1).
    """
    row, _ = AccountStatus.objects.get_or_create(user=user)
    row = AccountStatus.objects.select_for_update().get(pk=row.pk)
    if row.state == DELETED:
        return False
    before_state = row.state

    revoke_all_sessions(user, actor=actor, reason=f"Account deleted: {reason}")
    user.password_reset_tokens.all().delete()

    for model in (UserTimetableEntry, UserTodoEntry, UserNoteEntry, UserGpaEntry):
        model.objects.filter(user=user).delete()
    UserPreferences.objects.filter(user=user).delete()
    UserDebaterProgress.objects.filter(user=user).delete()
    AccountDeletionRequest.objects.filter(user=user).delete()
    ContactMessage.objects.filter(user=user).update(name="", email="")
    UserProfile.objects.filter(user=user).update(
        phone="", network="", student_id="", matric_number=""
    )

    user.username = f"deleted-{user.pk}"
    user.email = ""
    user.first_name = ""
    user.last_name = ""
    user.is_active = False
    user.is_staff = False
    user.is_superuser = False
    user.set_unusable_password()
    user.save()

    row.state = DELETED
    row.reason = reason
    row.changed_by = actor
    row.save()
    # No username or email in the audit row: it must not carry the personal data we just removed.
    log_audit(
        actor=actor,
        action="account.anonymised",
        target_type="User",
        target_id=user.pk,
        before={"state": before_state},
        after={"state": DELETED},
        reason=reason,
    )
    return True