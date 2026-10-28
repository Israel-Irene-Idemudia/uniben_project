import re

from django.db import transaction

from common.models import SETTING_KEY_PATTERN, AuditLog, PlatformSetting
from common.request_context import get_request_id


def _actor_label(actor):
    return actor.get_username() if actor is not None else "system"


def _clean_reason(reason):
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("A reason is required.")
    return reason


def log_audit(
    *,
    actor,
    action,
    target_type,
    target_id,
    before=None,
    after=None,
    reason="",
    request_id=None,
):
    """Append one row to the audit log. The only way code should write it."""
    return AuditLog.objects.create(
        actor=actor,
        actor_label=_actor_label(actor),
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        before=before,
        after=after,
        reason=reason,
        request_id=request_id or get_request_id() or "",
    )


def get_setting(key, default=None):
    try:
        return PlatformSetting.objects.get(key=key).value
    except PlatformSetting.DoesNotExist:
        return default


@transaction.atomic
def set_setting(key, value, *, actor, reason, description=None, request_id=None):
    """Create or change a setting and audit it in the same transaction.

    A reason is mandatory. Setting the same value again writes nothing.
    """
    reason = _clean_reason(reason)
    if not re.fullmatch(SETTING_KEY_PATTERN, key or ""):
        raise ValueError("Invalid setting key.")

    # Row lock so two admins editing one key cannot interleave
    # (a no-op on SQLite, effective on PostgreSQL).
    existing = PlatformSetting.objects.select_for_update().filter(key=key).first()

    if existing is None:
        setting = PlatformSetting.objects.create(
            key=key,
            value=value,
            description=description or "",
            updated_by=actor,
        )
        log_audit(
            actor=actor,
            action="setting.create",
            target_type="PlatformSetting",
            target_id=key,
            before=None,
            after={"value": value, "description": setting.description},
            reason=reason,
            request_id=request_id,
        )
        return setting

    new_description = existing.description if description is None else description
    if existing.value == value and existing.description == new_description:
        return existing

    before = {"value": existing.value, "description": existing.description}
    existing.value = value
    existing.description = new_description
    existing.updated_by = actor
    existing.save()
    log_audit(
        actor=actor,
        action="setting.update",
        target_type="PlatformSetting",
        target_id=key,
        before=before,
        after={"value": value, "description": new_description},
        reason=reason,
        request_id=request_id,
    )
    return existing