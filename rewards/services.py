"""Redeeming a reward, shared by the legacy and v1 endpoints (D7: server authority).

The price comes from RewardCatalog, never from the request. The points move
through xp.services.spend_points, which locks the student and refuses to go
below zero.
"""
import uuid

from django.db import transaction

from accounts.models import UserProfile
from xp.services import spend_points

from .models import Redemption, RewardCatalog


class UnknownReward(Exception):
    """reward_type is not in the catalogue, or is switched off."""


class ProfileMissing(Exception):
    pass


def redeem_reward(user, *, reward_type, phone, network, idempotency_key=None):
    """Create a Redemption and the ledger spend that pays for it, atomically.

    InsufficientPoints (from the ledger) propagates; because it is raised
    inside the atomic block, the half-made Redemption row is rolled back.

    The legacy endpoint has no idempotency key from the client, so a fresh one
    is generated: retries on that route stay exactly as unsafe as before. The
    v1 endpoint passes its Idempotency-Key header through.
    """
    # Exact match on purpose: the catalogue is seeded from real history, and
    # a loose match could price a typo at the wrong reward.
    reward = RewardCatalog.objects.filter(reward_type=(reward_type or "").strip(), is_active=True).first()
    if reward is None:
        raise UnknownReward(reward_type)
    if not UserProfile.objects.filter(user=user).exists():
        raise ProfileMissing()

    key = idempotency_key or f"redeem:{uuid.uuid4().hex}"
    with transaction.atomic():
        redemption = Redemption.objects.create(
            user=user,
            reward_type=reward.reward_type,
            point_cost=reward.point_cost,
            phone=phone,
            network=network,
            status="pending",
        )
        entry = spend_points(
            user,
            cost=reward.point_cost,
            reason_code="reward_redeem",
            source_feature="rewards",
            source_record_id=str(redemption.pk),
            idempotency_key=key,
            metadata={"reward_type": reward.reward_type},
        )
        redemption.ledger_entry = entry
        redemption.save(update_fields=["ledger_entry"])
        # Same side effect as before: remember the student's phone and network.
        updates = {}
        if phone:
            updates["phone"] = phone
        if network:
            updates["network"] = network
        if updates:
            UserProfile.objects.filter(user=user).update(**updates)
    return redemption
