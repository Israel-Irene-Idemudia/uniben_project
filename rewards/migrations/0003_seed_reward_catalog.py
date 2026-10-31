"""Seed the reward price list from what students actually redeemed (D-1).

DECISION (D-1): the real price table lives in the Flutter code, which the
build cannot see. Rather than invent prices, each reward_type seen in past
redemptions is added at its MOST COMMON historical cost (ties: the higher
cost). On a database with no redemptions nothing is seeded.

Because the old API let the client choose the price, a few historical rows may
be underpriced. ISRAEL MUST OPEN ADMIN -> Reward catalogue AFTER DEPLOY (or
after the rehearsal) AND CHECK EVERY PRICE. Any reward missing from the
catalogue is refused with 400 until it is added.

Idempotent (get_or_create) and never overwrites an edited row. Reverse is a
no-op so a rollback cannot delete admin-edited prices.
"""
from django.db import migrations
from django.db.models import Count


def seed(apps, schema_editor):
    Redemption = apps.get_model("rewards", "Redemption")
    RewardCatalog = apps.get_model("rewards", "RewardCatalog")

    best = {}  # reward_type -> (count, cost)
    rows = Redemption.objects.values("reward_type", "point_cost").annotate(n=Count("id"))
    for row in rows:
        reward_type = (row["reward_type"] or "").strip()
        if not reward_type or row["point_cost"] <= 0:
            continue
        candidate = (row["n"], row["point_cost"])
        if reward_type not in best or candidate > best[reward_type]:
            best[reward_type] = candidate

    for reward_type, (_count, cost) in best.items():
        RewardCatalog.objects.get_or_create(
            reward_type=reward_type, defaults={"point_cost": cost, "is_active": True}
        )


class Migration(migrations.Migration):
    dependencies = [("rewards", "0002_reward_catalog")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
