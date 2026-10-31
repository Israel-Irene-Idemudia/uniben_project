"""The only place contribution rule sets change state (Phase 4.2).

Every write is audited with a mandatory reason. Activation needs the
`leaderboards.activate_contributionruleset` permission (superusers have it),
so an ordinary staff editor can prepare a draft but cannot publish it.

Locking: activation locks the draft and every active set in the same scope,
so two admins cannot publish two rules for one university at once. The
partial unique constraints are the last line of defence. (Row locks are
no-ops on SQLite; effective on PostgreSQL.)
"""
from decimal import Decimal
from typing import Iterable, Mapping, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from common.services import log_audit

from .models import ContributionRuleItem, ContributionRuleSet

ACTIVATE_PERMISSION = "leaderboards.activate_contributionruleset"


class RuleSetError(Exception):
    """An expected, user-facing refusal. `problems` lists every reason."""

    def __init__(self, problems):
        if isinstance(problems, str):
            problems = [problems]
        self.problems = list(problems)
        super().__init__(" ".join(self.problems))


def _reason(reason: str) -> str:
    reason = (reason or "").strip()
    if not reason:
        raise RuleSetError("A reason is required.")
    return reason


def _require_activate_permission(actor) -> None:
    if actor is None or not actor.has_perm(ACTIVATE_PERMISSION):
        raise RuleSetError("You do not have permission to activate or retire contribution rules.")


def snapshot(rule_set: ContributionRuleSet) -> dict:
    """Plain-JSON copy of a rule set and its items, for the audit log."""
    return {
        "name": rule_set.name,
        "university_id": rule_set.university_id,
        "summary": rule_set.summary,
        "student_cap": rule_set.student_cap,
        "uncapped": rule_set.uncapped,
        "state": rule_set.state,
        "items": [
            {
                "action_code": item.xp_rule.action_code,
                "label": item.label,
                "weight": None if item.weight is None else str(item.weight),
                "per_student_cap": item.per_student_cap,
            }
            for item in rule_set.items.select_related("xp_rule").order_by("id")
        ],
    }


def _validation_problems(exc: ValidationError) -> list:
    if hasattr(exc, "message_dict"):
        return [f"{field}: {msg}" for field, msgs in exc.message_dict.items() for msg in msgs]
    return list(exc.messages)


def create_draft(
    *, name: str, university=None, summary: str = "", student_cap: Optional[int] = None,
    uncapped: bool = False, actor, reason: str,
) -> ContributionRuleSet:
    reason = _reason(reason)
    rule_set = ContributionRuleSet(
        name=(name or "").strip(), university=university, summary=summary or "",
        student_cap=student_cap, uncapped=uncapped,
    )
    try:
        rule_set.full_clean()
    except ValidationError as exc:
        raise RuleSetError(_validation_problems(exc))
    with transaction.atomic():
        rule_set.save()
        record_draft_edit(rule_set, before=None, actor=actor, reason=reason)
    return rule_set


def set_item(
    rule_set: ContributionRuleSet, *, xp_rule, label: str = "", weight=None,
    per_student_cap: Optional[int] = None, actor, reason: str,
) -> ContributionRuleItem:
    """Add or replace one activity on a DRAFT. Audited."""
    reason = _reason(reason)
    with transaction.atomic():
        rule_set = ContributionRuleSet.objects.select_for_update().get(pk=rule_set.pk)
        if rule_set.state != ContributionRuleSet.STATE_DRAFT:
            raise RuleSetError("Only a draft rule set can be changed. Copy it to a new draft.")
        before = snapshot(rule_set)
        item = rule_set.items.filter(xp_rule=xp_rule).first() or ContributionRuleItem(
            rule_set=rule_set, xp_rule=xp_rule
        )
        item.label = (label or "").strip()
        item.weight = None if weight is None else Decimal(str(weight))
        item.per_student_cap = per_student_cap
        try:
            item.full_clean()
        except ValidationError as exc:
            raise RuleSetError(_validation_problems(exc))
        item.save()
        record_draft_edit(rule_set, before=before, actor=actor, reason=reason)
    return item


def record_draft_edit(rule_set: ContributionRuleSet, *, before: Optional[dict], actor, reason: str) -> None:
    """Audit a draft create or edit. Writes nothing if nothing changed."""
    after = snapshot(rule_set)
    if before is not None and before == after:
        return
    log_audit(
        actor=actor,
        action="contribution_rules.create" if before is None else "contribution_rules.update",
        target_type="ContributionRuleSet",
        target_id=rule_set.pk,
        before=before,
        after=after,
        reason=_reason(reason),
    )


def readiness_problems(rule_set: ContributionRuleSet) -> list:
    """Everything that stops this draft being activated. Empty = ready.

    Incomplete rules stay inactive: nothing here fills a gap with a default.
    """
    problems = []
    if rule_set.state != ContributionRuleSet.STATE_DRAFT:
        problems.append(f"Only a draft can be activated; this one is {rule_set.state}.")
    if not (rule_set.name or "").strip():
        problems.append("A name is required.")
    if not (rule_set.summary or "").strip():
        problems.append("A student-facing summary is required.")
    if rule_set.student_cap is None and not rule_set.uncapped:
        problems.append("Set a per-student cap, or tick 'uncapped' to publish with no cap on purpose.")
    if rule_set.student_cap is not None and rule_set.uncapped:
        problems.append("Set a per-student cap or tick 'uncapped', not both.")
    if rule_set.university_id is not None and not rule_set.university.is_active:
        problems.append("The university is not active.")
    items = list(rule_set.items.select_related("xp_rule").order_by("id"))
    if not items:
        problems.append("Add at least one contributing activity.")
    for item in items:
        code = item.xp_rule.action_code
        if item.weight is None:
            problems.append(f"{code}: a weight is required.")
        if not (item.label or "").strip():
            problems.append(f"{code}: a student-facing label is required.")
        if not item.xp_rule.is_active:
            problems.append(f"{code}: this XP rule is switched off.")
    return problems


def _same_scope(rule_set: ContributionRuleSet):
    return ContributionRuleSet.objects.filter(
        state=ContributionRuleSet.STATE_ACTIVE, university_id=rule_set.university_id
    )


def activate_rule_set(rule_set: ContributionRuleSet, *, actor, reason: str) -> ContributionRuleSet:
    """Publish a complete draft. The previous active set in the same scope
    (same university, or global) is retired in the same transaction.

    New rules apply to boards computed from now on. Boards archived at a
    season close (Phase 4.6) keep the rule they were computed with.
    """
    reason = _reason(reason)
    _require_activate_permission(actor)
    with transaction.atomic():
        rule_set = ContributionRuleSet.objects.select_for_update().get(pk=rule_set.pk)
        problems = readiness_problems(rule_set)
        if problems:
            raise RuleSetError(problems)
        now = timezone.now()
        for previous in _same_scope(rule_set).select_for_update():
            before = snapshot(previous)
            previous.state = ContributionRuleSet.STATE_RETIRED
            previous.retired_at = now
            previous.save(update_fields=["state", "retired_at", "updated_at"])
            log_audit(
                actor=actor, action="contribution_rules.retire", target_type="ContributionRuleSet",
                target_id=previous.pk, before=before, after=snapshot(previous),
                reason=f"Replaced by rule set {rule_set.pk}: {reason}",
            )
        before = snapshot(rule_set)
        rule_set.state = ContributionRuleSet.STATE_ACTIVE
        rule_set.activated_at = now
        rule_set.activated_by = actor
        rule_set.save(update_fields=["state", "activated_at", "activated_by", "updated_at"])
        log_audit(
            actor=actor, action="contribution_rules.activate", target_type="ContributionRuleSet",
            target_id=rule_set.pk, before=before, after=snapshot(rule_set), reason=reason,
        )
    return rule_set


def retire_rule_set(rule_set: ContributionRuleSet, *, actor, reason: str) -> ContributionRuleSet:
    """Withdraw an active set. A university then falls back to the global
    set, or to no published rule at all. Retired is final."""
    reason = _reason(reason)
    _require_activate_permission(actor)
    with transaction.atomic():
        rule_set = ContributionRuleSet.objects.select_for_update().get(pk=rule_set.pk)
        if rule_set.state != ContributionRuleSet.STATE_ACTIVE:
            raise RuleSetError(f"A {rule_set.state} rule set cannot be retired.")
        before = snapshot(rule_set)
        rule_set.state = ContributionRuleSet.STATE_RETIRED
        rule_set.retired_at = timezone.now()
        rule_set.save(update_fields=["state", "retired_at", "updated_at"])
        log_audit(
            actor=actor, action="contribution_rules.retire", target_type="ContributionRuleSet",
            target_id=rule_set.pk, before=before, after=snapshot(rule_set), reason=reason,
        )
    return rule_set



def copy_to_draft(rule_set: ContributionRuleSet, *, actor, reason: str) -> ContributionRuleSet:
    """The only way to change a published rule: copy, edit, activate."""
    reason = _reason(reason)
    with transaction.atomic():
        copy = ContributionRuleSet.objects.create(
            name=rule_set.name, university_id=rule_set.university_id, summary=rule_set.summary,
            student_cap=rule_set.student_cap, uncapped=rule_set.uncapped,
        )
        for item in rule_set.items.order_by("id"):
            ContributionRuleItem.objects.create(
                rule_set=copy, xp_rule_id=item.xp_rule_id, label=item.label,
                weight=item.weight, per_student_cap=item.per_student_cap,
            )
        log_audit(
            actor=actor, action="contribution_rules.create", target_type="ContributionRuleSet",
            target_id=copy.pk, before=None, after=snapshot(copy),
            reason=f"Copied from rule set {rule_set.pk}: {reason}",
        )
    return copy


def get_active_rule_set(university=None) -> Optional[ContributionRuleSet]:
    """The rule that applies to a university: its own active set, else the
    global active set, else None. Pass None for 'no university known'.

    Does not decide whether universities share a rule (D-16 is open): with
    only a global set every university shares it; adding a university's own
    set overrides it for that university only.
    """
    active = (
        ContributionRuleSet.objects.filter(state=ContributionRuleSet.STATE_ACTIVE)
        .select_related("university")
        .prefetch_related("items__xp_rule")
    )
    university_id = getattr(university, "pk", university)
    if university_id is not None:
        own = active.filter(university_id=university_id).first()
        if own is not None:
            return own
    return active.filter(university__isnull=True).first()


def compute_contribution(rule_set: ContributionRuleSet, xp_by_action: Mapping[str, int]) -> Decimal:
    """One student's contribution under a rule set (for Phase 4.3 boards).

    xp_by_action: XP the student earned in the board period, keyed by
    action_code (the reason_code of award rows), summed from the ledger by
    the caller. Activities not in the rule contribute nothing. Each activity
    is weight x XP, limited by its own cap; the total is then limited by the
    rule set's per-student cap unless the set is deliberately uncapped.
    """
    total = Decimal("0")
    for item in rule_set.items.all():
        if item.weight is None:
            raise RuleSetError(f"{item.xp_rule.action_code}: a weight is required.")
        xp = max(int(xp_by_action.get(item.xp_rule.action_code, 0) or 0), 0)
        points = item.weight * xp
        if item.per_student_cap is not None:
            points = min(points, Decimal(item.per_student_cap))
        total += points
    if not rule_set.uncapped and rule_set.student_cap is not None:
        total = min(total, Decimal(rule_set.student_cap))
    return total


def contributing_action_codes(rule_set: ContributionRuleSet) -> Iterable[str]:
    return [item.xp_rule.action_code for item in rule_set.items.all()]

