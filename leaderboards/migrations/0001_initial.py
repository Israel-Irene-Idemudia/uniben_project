# Additive: two new tables. Safe on a live database. Seeds nothing (D-18).
import django.core.validators
import django.db.models.deletion
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0007_seed_uniben"),
        ("xp", "0003_opening_balances"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContributionRuleSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("summary", models.TextField(blank=True, help_text="Student-facing explanation. Both apps show it exactly as written.")),
                ("student_cap", models.PositiveIntegerField(blank=True, help_text="Most contribution points one student can add per board period.", null=True, validators=[django.core.validators.MinValueValidator(1)])),
                ("uncapped", models.BooleanField(default=False, help_text="Tick only to publish with no per-student cap on purpose.")),
                ("state", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("retired", "Retired")], default="draft", max_length=10)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("retired_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("activated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("university", models.ForeignKey(blank=True, help_text="Empty = applies to every university that has no active rule set of its own.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="contribution_rule_sets", to="core.university")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "permissions": [("activate_contributionruleset", "Can activate or retire contribution rule sets")],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("state", "active"), ("university__isnull", False)), fields=("university",), name="uniq_active_rule_set_per_university"),
                    models.UniqueConstraint(condition=models.Q(("state", "active"), ("university__isnull", True)), fields=("state",), name="uniq_active_global_rule_set"),
                    models.CheckConstraint(condition=models.Q(("uncapped", False), ("student_cap__isnull", True), _connector="OR"), name="rule_set_cap_or_uncapped"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ContributionRuleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, help_text="Student-facing name of the activity.", max_length=100)),
                ("weight", models.DecimalField(blank=True, decimal_places=2, help_text="Contribution points per 1 XP earned from this activity.", max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("per_student_cap", models.PositiveIntegerField(blank=True, help_text="Optional: most contribution points one student can add from this activity.", null=True, validators=[django.core.validators.MinValueValidator(1)])),
                ("rule_set", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="leaderboards.contributionruleset")),
                ("xp_rule", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contribution_items", to="xp.xprule")),
            ],
            options={
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(fields=("rule_set", "xp_rule"), name="uniq_rule_item_per_action"),
                    models.CheckConstraint(condition=models.Q(("weight__isnull", True), ("weight__gt", 0), _connector="OR"), name="rule_item_weight_positive"),
                ],
            },
        ),
    ]
