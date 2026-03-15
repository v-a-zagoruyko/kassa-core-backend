"""Tests for AcquiringService stub and PaymentMethod."""

import decimal
import pytest
from unittest.mock import MagicMock

from payments.acquiring import AcquiringService
from payments.models import Payment, PaymentMethod, PaymentTransaction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def payment_method(db):
    return PaymentMethod.objects.create(
        name="card",
        display_name="Банковская карта",
        is_active=True,
    )


@pytest.fixture
def store(db):
    from common.models import Address
    from stores.models import Store
    address = Address.objects.create(city="Г", street="У", house="1")
    return Store.objects.create(name="PayStore", address=address)


@pytest.fixture
def order(db, store):
    from orders.models import Order
    return Order.objects.create(
        store=store,
        status=Order.Status.PENDING_PAYMENT,
        total_amount=decimal.Decimal("500.00"),
        final_amount=decimal.Decimal("500.00"),
        payment_method=Order.PaymentMethod.CARD,
    )


@pytest.fixture
def payment(order, payment_method):
    return Payment.objects.create(
        order=order,
        amount=decimal.Decimal("500.00"),
        currency="RUB",
        method=payment_method,
        status=Payment.Status.PROCESSING,
        acquiring_payment_id="ACQ-123",
    )


# ---------------------------------------------------------------------------
# AcquiringService stub
# ---------------------------------------------------------------------------

class TestAcquiringServiceStub:
    def test_initiate_returns_payment_id_and_url(self):
        mock_payment = MagicMock()
        mock_payment.id = "order-123"
        mock_payment.amount = decimal.Decimal("199.00")
        result = AcquiringService.initiate_payment(mock_payment)
        assert "acquiring_payment_id" in result
        assert "payment_url" in result

    def test_parse_webhook_extracts_status(self):
        # handle_webhook reads "payment_id" from payload
        payload = {
            "payment_id": "TEST-001",
            "status": "completed",
            "amount": "199.00",
            "transaction_id": "TXN-001",
        }
        parsed = AcquiringService.handle_webhook(payload)
        assert parsed["acquiring_payment_id"] == "TEST-001"
        assert parsed["status"] == "completed"

    def test_refund_returns_transaction_id(self):
        mock_payment = MagicMock()
        result = AcquiringService.refund(mock_payment, amount=decimal.Decimal("100.00"))
        assert "transaction_id" in result


# ---------------------------------------------------------------------------
# PaymentMethod model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentMethodModel:
    def test_create_payment_method(self):
        pm = PaymentMethod.objects.create(name="cash", display_name="Наличные", is_active=True)
        assert pm.name == "cash"
        assert pm.is_active is True

    def test_payment_method_name_unique(self, payment_method):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PaymentMethod.objects.create(name="card", display_name="Дубль", is_active=True)

    def test_payment_method_str(self, payment_method):
        assert "card" in str(payment_method) or "Банковская карта" in str(payment_method)

    def test_inactive_payment_method(self):
        pm = PaymentMethod.objects.create(name="qr_inactive", display_name="QR", is_active=False)
        assert pm.is_active is False


# ---------------------------------------------------------------------------
# Payment model — additional coverage
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentModelAdditional:
    def test_payment_str(self, payment):
        s = str(payment)
        assert s  # non-empty

    def test_payment_default_currency_rub(self, order, payment_method):
        p = Payment.objects.create(
            order=order,
            amount=decimal.Decimal("100.00"),
            method=payment_method,
        )
        assert p.currency == "RUB"

    def test_payment_acquiring_data_json(self, order, payment_method):
        p = Payment.objects.create(
            order=order,
            amount=decimal.Decimal("100.00"),
            method=payment_method,
            acquiring_data={"key": "value"},
        )
        p.refresh_from_db()
        assert p.acquiring_data["key"] == "value"


# ---------------------------------------------------------------------------
# PaymentTransaction model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPaymentTransactionModel:
    def test_create_charge_transaction(self, payment):
        txn = PaymentTransaction.objects.create(
            payment=payment,
            transaction_type=PaymentTransaction.TransactionType.CHARGE,
            amount=decimal.Decimal("500.00"),
            status=PaymentTransaction.Status.SUCCESS,
            acquiring_transaction_id="TXN-C-001",
        )
        assert txn.transaction_type == PaymentTransaction.TransactionType.CHARGE
        assert txn.status == PaymentTransaction.Status.SUCCESS

    def test_create_refund_transaction(self, payment):
        txn = PaymentTransaction.objects.create(
            payment=payment,
            transaction_type=PaymentTransaction.TransactionType.REFUND,
            amount=decimal.Decimal("200.00"),
            status=PaymentTransaction.Status.PENDING,
            acquiring_transaction_id="TXN-R-001",
        )
        assert txn.transaction_type == PaymentTransaction.TransactionType.REFUND

    def test_transaction_cascade_on_payment_delete(self, payment):
        PaymentTransaction.objects.create(
            payment=payment,
            transaction_type=PaymentTransaction.TransactionType.CHARGE,
            amount=decimal.Decimal("500.00"),
            status=PaymentTransaction.Status.SUCCESS,
            acquiring_transaction_id="TXN-D-001",
        )
        payment_id = payment.id
        payment.hard_delete()
        assert PaymentTransaction.objects.filter(payment_id=payment_id).count() == 0

    def test_transaction_raw_data_json(self, payment):
        txn = PaymentTransaction.objects.create(
            payment=payment,
            transaction_type=PaymentTransaction.TransactionType.CHARGE,
            amount=decimal.Decimal("500.00"),
            status=PaymentTransaction.Status.SUCCESS,
            raw_data={"key": "val"},
        )
        txn.refresh_from_db()
        assert txn.raw_data["key"] == "val"
