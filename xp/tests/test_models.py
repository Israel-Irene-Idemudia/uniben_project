from django.db import IntegrityError, transaction
from django.test import TestCase

from common.models import ImmutableRecordError
from xp.models import XPLedgerEntry

from .helpers import make_student


def _row(user, **overrides):
    data = dict(
        user=user, amount=5, kind="award", reason_code="x", source_feature="t",
        source_record_id="1", idempotency_key="k1",
    )
    data.update(overrides)
    return XPLedgerEntry.objects.create(**data)


class LedgerImmutabilityTests(TestCase):
    def setUp(self):
        self.user = make_student()
        self.row = _row(self.user)

    def test_saved_row_cannot_be_changed(self):
        self.row.amount = 999
        with self.assertRaises(ImmutableRecordError):
            self.row.save()

    def test_row_cannot_be_deleted(self):
        with self.assertRaises(ImmutableRecordError):
            self.row.delete()

    def test_queryset_update_and_delete_are_blocked(self):
        with self.assertRaises(ImmutableRecordError):
            XPLedgerEntry.objects.all().update(amount=1)
        with self.assertRaises(ImmutableRecordError):
            XPLedgerEntry.objects.all().delete()
        with self.assertRaises(ImmutableRecordError):
            XPLedgerEntry.objects.bulk_update([self.row], ["amount"])
        self.assertEqual(XPLedgerEntry.objects.get(pk=self.row.pk).amount, 5)


class LedgerConstraintTests(TestCase):
    def setUp(self):
        self.user = make_student()

    def assertRejected(self, **overrides):
        with self.assertRaises(IntegrityError), transaction.atomic():
            _row(self.user, **overrides)

    def test_duplicate_key_for_same_user_is_rejected(self):
        _row(self.user, idempotency_key="dup")
        self.assertRejected(idempotency_key="dup")

    def test_same_key_for_another_user_is_allowed(self):
        _row(self.user, idempotency_key="shared")
        _row(make_student("other"), idempotency_key="shared")

    def test_amount_must_match_kind(self):
        self.assertRejected(kind="award", amount=-1, idempotency_key="a")
        self.assertRejected(kind="spend", amount=5, idempotency_key="b")
        self.assertRejected(kind="spend", amount=0, idempotency_key="c")
        self.assertRejected(kind="adjustment", amount=0, idempotency_key="d")
        self.assertRejected(kind="opening_balance", amount=0, idempotency_key="e")
