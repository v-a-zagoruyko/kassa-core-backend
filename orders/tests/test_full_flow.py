"""
Integration test: full order lifecycle.

Flow:
1. Create Store + Kiosk + Product + Stock
2. Create Order (delivery), add OrderItem
3. Submit order → Reservation created, stock decremented
4. Payment initiated → webhook processed → Order.status = PAID
5. Receipt generated
"""

import decimal
from unittest.mock import MagicMock, patch

import pytest

from common.models import Address
from fiscal.models import Receipt
from fiscal.services import ReceiptService
from orders.models import Order, OrderItem, Reservation
from orders.services.order_service import OrderService
from payments.models import Payment, PaymentMethod, PaymentTransaction
from payments.services import PaymentService
from products.models import Category, Product, Stock
from stores.models import Kiosk, Store


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def address(db):
    return Address.objects.create(city="Тюмень", street="Ленина", house="1")


@pytest.fixture
def delivery_address(db):
    return Address.objects.create(city="Тюмень", street="Мира", house="5", apartment="10")


@pytest.fixture
def store(address):
    return Store.objects.create(name="Флагманский", address=address)


@pytest.fixture
def kiosk(store):
    return Kiosk.objects.create(store=store, kiosk_number="K01", is_active=True)


@pytest.fixture
def category():
    return Category.objects.create(name="Молочные продукты")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Молоко",
        category=category,
        price=decimal.Decimal("120.00"),
        is_active=True,
    )


@pytest.fixture
def stock(product, store):
    return Stock.objects.create(
        product=product,
        store=store,
        quantity=decimal.Decimal("50"),
    )


@pytest.fixture
def payment_method(db):
    return PaymentMethod.objects.create(
        name="card",
        display_name="Банковская карта",
        is_active=True,
    )


@pytest.fixture
def customer(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username="buyer", password="pass")


# ---------------------------------------------------------------------------
# Full flow integration test
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFullOrderFlow:
    def test_create_and_submit_order(self, customer, store, product, stock, delivery_address):
        """Steps 1–3: create order, add items, submit."""
        # Step 1: Create order
        order = OrderService.create_order(
            customer,
            store.id,
            order_type="delivery",
            delivery_address_id=delivery_address.id,
        )
        assert order.status == Order.Status.DRAFT
        assert order.order_type == "delivery"

        # Step 2: Add item
        item = OrderService.add_item(order.id, product.id, 3)
        assert item.quantity == 3
        assert item.subtotal == decimal.Decimal("360.00")

        # Step 3: Submit order → PENDING, reservation created
        order = OrderService.submit_order(order.id)
        assert order.status == Order.Status.PENDING

        reservation = Reservation.objects.get(order=order, product=product)
        assert reservation.status == Reservation.Status.ACTIVE
        assert reservation.quantity == decimal.Decimal("3")

        # Stock should be decremented by 3
        stock.refresh_from_db()
        assert stock.quantity == decimal.Decimal("47")

    def test_payment_webhook_completes_order(
        self, customer, store, product, stock, delivery_address, payment_method
    ):
        """Steps 4: payment webhook → Order.PAID, reservations completed."""
        order = OrderService.create_order(
            customer, store.id,
            order_type="delivery",
            delivery_address_id=delivery_address.id,
        )
        OrderService.add_item(order.id, product.id, 2)
        order = OrderService.submit_order(order.id)

        # Manually transition to PENDING_PAYMENT (simulate payment initiation)
        order.status = Order.Status.PENDING_PAYMENT
        order.save()

        # Create a Payment record as PaymentService.initiate_payment would
        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            currency="RUB",
            method=payment_method,
            status=Payment.Status.PROCESSING,
            acquiring_payment_id="TEST-ACQ-001",
        )

        # Simulate completed webhook payload
        # AcquiringService.handle_webhook reads "payment_id" key from payload
        payload = {
            "payment_id": "TEST-ACQ-001",
            "status": "completed",
            "amount": str(order.total_amount),
            "transaction_id": "TXN-001",
        }

        updated_payment = PaymentService.process_webhook(payload)

        updated_payment.refresh_from_db()
        assert updated_payment.status == Payment.Status.COMPLETED

        order.refresh_from_db()
        assert order.status == Order.Status.PAID

        reservation = Reservation.objects.get(order=order, product=product)
        assert reservation.status == Reservation.Status.COMPLETED

    def test_generate_receipt_after_payment(
        self, customer, store, product, stock, delivery_address, payment_method
    ):
        """Step 5: generate receipt for paid order."""
        order = OrderService.create_order(
            customer, store.id,
            order_type="delivery",
            delivery_address_id=delivery_address.id,
        )
        OrderService.add_item(order.id, product.id, 1)
        order = OrderService.submit_order(order.id)

        # Force to PAID status
        order.status = Order.Status.PAID
        order.total_amount = decimal.Decimal("120.00")
        order.final_amount = decimal.Decimal("120.00")
        order.save()

        receipt = ReceiptService.generate_receipt(order_id=order.id)

        assert receipt.status == Receipt.Status.PENDING
        assert receipt.receipt_number.startswith("RCP-")
        assert receipt.items.count() == 1
        assert receipt.fiscal_data["type"] == "income"

    def test_cancel_order_releases_reservation(
        self, customer, store, product, stock, delivery_address
    ):
        """Cancel flow: reservations released, stock restored."""
        initial_qty = stock.quantity

        order = OrderService.create_order(
            customer, store.id,
            order_type="delivery",
            delivery_address_id=delivery_address.id,
        )
        OrderService.add_item(order.id, product.id, 4)
        order = OrderService.submit_order(order.id)

        stock.refresh_from_db()
        assert stock.quantity == initial_qty - decimal.Decimal("4")

        order = OrderService.cancel_order(order.id)
        assert order.status == Order.Status.CANCELLED

        stock.refresh_from_db()
        assert stock.quantity == initial_qty

        reservation = Reservation.objects.get(order=order, product=product)
        assert reservation.status == Reservation.Status.RELEASED


@pytest.mark.django_db
class TestKioskOrderFlow:
    """Quick kiosk order flow."""

    def test_kiosk_order_created(self, store, kiosk, customer, product, stock):
        order = OrderService.create_order(
            customer, store.id, order_type="kiosk"
        )
        assert order.order_type == "kiosk"

        item = OrderService.add_item(order.id, product.id, 1)
        assert item.quantity == 1

    def test_pickup_order_no_address_required(self, store, customer, product, stock):
        order = OrderService.create_order(customer, store.id, order_type="pickup")
        OrderService.add_item(order.id, product.id, 1)
        submitted = OrderService.submit_order(order.id)
        assert submitted.status == Order.Status.PENDING


@pytest.mark.django_db
class TestDeliveryOrderFields:
    """Tests for delivery-specific order fields."""

    def test_order_delivery_status_default_none(self, store):
        order = Order.objects.create(store=store)
        assert order.delivery_status is None

    def test_order_delivery_status_can_be_set(self, store):
        order = Order.objects.create(
            store=store,
            delivery_status=Order.DeliveryStatus.PENDING,
        )
        assert order.delivery_status == Order.DeliveryStatus.PENDING

    def test_order_estimated_delivery_at(self, store):
        from django.utils import timezone
        from datetime import timedelta
        eta = timezone.now() + timedelta(hours=2)
        order = Order.objects.create(store=store, estimated_delivery_at=eta)
        assert order.estimated_delivery_at is not None

    def test_order_delivery_cost_default_zero(self, store):
        order = Order.objects.create(store=store)
        assert order.delivery_cost == decimal.Decimal("0")

    def test_order_courier_comment(self, store):
        order = Order.objects.create(
            store=store,
            courier_comment="Позвонить в домофон 42",
        )
        assert order.courier_comment == "Позвонить в домофон 42"

    def test_order_type_choices(self, store):
        for order_type in [Order.OrderType.DELIVERY, Order.OrderType.PICKUP, Order.OrderType.KIOSK]:
            order = Order.objects.create(store=store, order_type=order_type)
            assert order.order_type == order_type
