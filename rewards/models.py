from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class RewardCatalog(models.Model):
    """The server-owned price list (decision D-1, decision D7).

    The client never sets a price. Every redemption looks its reward_type up
    here. Edit prices in admin (reason required, audited). Retire a reward with
    is_active off; never delete.
    """

    reward_type = models.CharField(max_length=100, unique=True)
    point_cost = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reward catalogue entry"
        verbose_name_plural = "Reward catalogue"
        ordering = ["point_cost", "reward_type"]

    def __str__(self):
        return f"{self.reward_type} ({self.point_cost} points)"


class Redemption(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Dispatch'),
        ('dispatched', 'Dispatched'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    reward_type = models.CharField(max_length=100)
    point_cost = models.IntegerField(default=50)
    phone = models.CharField(max_length=20)
    network = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    # The ledger spend that paid for this redemption. Null for redemptions made
    # before the ledger existed. PROTECT: a spend row cannot vanish under it.
    ledger_entry = models.OneToOneField(
        "xp.XPLedgerEntry",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="redemption",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.reward_type} ({self.status})"
