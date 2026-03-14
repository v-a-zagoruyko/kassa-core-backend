"""Тесты моделей фискального домена."""

from decimal import Decimal

import pytest

from fiscal.models import OFDResponse, Receipt, ReceiptItem, ReceiptStatus


@pytest.mark.django_db
class TestReceiptCreation:
    def test_receipt_created_with_receipt_number(self, paid_order):
        receipt = Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={'type': 'income', 'total': '100.00'},
        )
        assert receipt.pk is not None
        assert receipt.receipt_number == 'RCP-20260314-000001'
        assert receipt.status == Receipt.Status.PENDING

    def test_receipt_number_is_unique(self, paid_order):
        from django.db import IntegrityError

        Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
        )
        with pytest.raises(IntegrityError):
            Receipt.objects.create(
                order=paid_order,
                receipt_number='RCP-20260314-000001',
                fiscal_data={},
            )

    def test_receipt_str(self, paid_order):
        receipt = Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
        )
        assert 'RCP-20260314-000001' in str(receipt)

    def test_status_history_created_on_receipt_creation(self, paid_order):
        receipt = Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
        )
        history = ReceiptStatus.objects.filter(receipt=receipt)
        assert history.count() == 1
        assert history.first().status == Receipt.Status.PENDING

    def test_status_history_created_on_status_change(self, paid_order):
        receipt = Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
        )
        receipt.status = Receipt.Status.SENT
        receipt.save()
        history = ReceiptStatus.objects.filter(receipt=receipt)
        assert history.count() == 2
        statuses = list(history.values_list('status', flat=True))
        assert Receipt.Status.PENDING in statuses
        assert Receipt.Status.SENT in statuses


@pytest.mark.django_db
class TestReceiptItem:
    def _make_receipt(self, paid_order):
        return Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
        )

    def test_total_calculated_on_save(self, paid_order):
        receipt = self._make_receipt(paid_order)
        item = ReceiptItem.objects.create(
            receipt=receipt,
            product_name='Товар',
            quantity=3,
            price=Decimal('50.00'),
        )
        assert item.total == Decimal('150.00')

    def test_tax_amount_calculated_on_save(self, paid_order):
        receipt = self._make_receipt(paid_order)
        # НДС 20%: tax = total * 20 / 120 = 150 * 20 / 120 = 25.00
        item = ReceiptItem.objects.create(
            receipt=receipt,
            product_name='Товар',
            quantity=3,
            price=Decimal('50.00'),
        )
        expected_tax = (Decimal('150.00') * Decimal('20') / Decimal('120')).quantize(Decimal('0.01'))
        assert item.tax_amount == expected_tax

    def test_default_tax_rate_is_20(self, paid_order):
        receipt = self._make_receipt(paid_order)
        item = ReceiptItem.objects.create(
            receipt=receipt,
            product_name='Товар',
            quantity=1,
            price=Decimal('100.00'),
        )
        assert item.tax_rate == Decimal('20.00')
