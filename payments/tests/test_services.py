"""
Тесты PaymentService.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch


@pytest.fixture
def store(db):
    from stores.models import Store
    from common.models import Address
    address = Address.objects.create(city="Тюмень", street="Ленина", house="1")
    return Store.objects.create(name="Test Store", address=address)


@pytest.fixture
def category(db):
    from products.models import Category
    return Category.objects.create(name="Test Category")


@pytest.fixture
def product(db, category):
    from products.models import Product
    return Product.objects.create(name="Test Product", category=category, price=Decimal("100.00"))


@pytest.fixture
def user(db):
    from accounts.models import User
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def stock(db, product, store):
    from products.models import Stock
    return Stock.objects.create(
        product=product,
        store=store,
        quantity=Decimal("10.000"),
        reserved_quantity=Decimal("0.000"),
    )


@pytest.fixture
def order(db, store, user):
    from orders.models import Order
    return Order.objects.create(
        store=store,
        customer=user,
        status=Order.Status.PENDING_PAYMENT,
        final_amount=Decimal("500.00"),
    )


@pytest.fixture
def order_item(db, order, product):
    from orders.models import OrderItem
    return OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=Decimal("250.00"),
        subtotal=Decimal("500.00"),
    )


@pytest.fixture
def payment_method(db):
    from payments.models import PaymentMethod
    return PaymentMethod.objects.create(name="card", display_name="Карта")


@pytest.mark.django_db(transaction=True)
def test_initiate_payment(order, payment_method):
    """initiate_payment создаёт Payment и возвращает URL."""
    from payments.services import PaymentService
    from payments.models import Payment

    payment, payment_url = PaymentService.initiate_payment(order.id, payment_method.id)

    assert payment.status == Payment.Status.PROCESSING
    assert payment.acquiring_payment_id is not None
    assert payment.acquiring_payment_id.startswith("mock_")
    assert "mock-acquiring.example.com" in payment_url
    assert payment.order == order
    assert payment.amount == Decimal("500.00")


@pytest.mark.django_db(transaction=True)
def test_process_webhook_completed(order, payment_method, order_item, stock):
    """process_webhook: status=completed → Payment completed, Order paid."""
    from payments.services import PaymentService
    from payments.models import Payment, PaymentTransaction
    from orders.models import Order, Reservation

    # Создаём резерв
    from orders.services.reservation_service import ReservationService
    ReservationService.reserve_products(order.id)

    # Инициируем платёж
    payment, _ = PaymentService.initiate_payment(order.id, payment_method.id)

    payload = {
        "payment_id": payment.acquiring_payment_id,
        "status": "completed",
        "transaction_id": "txn_test_001",
        "amount": "500.00",
    }

    updated_payment = PaymentService.process_webhook(payload)

    assert updated_payment.status == Payment.Status.COMPLETED
    assert updated_payment.completed_at is not None

    order.refresh_from_db()
    assert order.status == Order.Status.PAID

    # Резервы должны быть завершены
    reservations = Reservation.objects.filter(order=order)
    for r in reservations:
        assert r.status == Reservation.Status.COMPLETED

    # Транзакция создана
    txn = PaymentTransaction.objects.get(payment=updated_payment)
    assert txn.status == PaymentTransaction.Status.SUCCESS


@pytest.mark.django_db(transaction=True)
def test_process_webhook_failed(order, payment_method, order_item, stock):
    """process_webhook: status=failed → Payment failed, Order cancelled."""
    from payments.services import PaymentService
    from payments.models import Payment, PaymentTransaction
    from orders.models import Order, Reservation

    # Создаём резерв
    from orders.services.reservation_service import ReservationService
    ReservationService.reserve_products(order.id)

    # Инициируем платёж
    payment, _ = PaymentService.initiate_payment(order.id, payment_method.id)

    payload = {
        "payment_id": payment.acquiring_payment_id,
        "status": "failed",
        "transaction_id": "txn_test_fail",
        "amount": "500.00",
        "failure_reason": "Card declined",
    }

    updated_payment = PaymentService.process_webhook(payload)

    assert updated_payment.status == Payment.Status.FAILED
    assert updated_payment.failed_at is not None

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED

    # Резервы освобождены
    reservations = Reservation.objects.filter(order=order)
    for r in reservations:
        assert r.status == Reservation.Status.RELEASED

    # Транзакция создана
    txn = PaymentTransaction.objects.get(payment=updated_payment)
    assert txn.status == PaymentTransaction.Status.FAILED


@pytest.mark.django_db(transaction=True)
def test_refund(order, payment_method):
    """refund: создаёт транзакцию возврата, меняет Payment.status."""
    from payments.services import PaymentService
    from payments.models import Payment, PaymentTransaction

    payment, _ = PaymentService.initiate_payment(order.id, payment_method.id)

    # Симулируем completed через webhook
    payload = {
        "payment_id": payment.acquiring_payment_id,
        "status": "completed",
        "transaction_id": "txn_test",
        "amount": "500.00",
    }
    PaymentService.process_webhook(payload)

    payment.refresh_from_db()
    txn = PaymentService.refund(payment.id)

    assert txn.transaction_type == PaymentTransaction.TransactionType.REFUND
    assert txn.status == PaymentTransaction.Status.SUCCESS
    assert txn.amount == Decimal("500.00")

    payment.refresh_from_db()
    assert payment.status == Payment.Status.REFUNDED


@pytest.mark.django_db(transaction=True)
def test_partial_refund(order, payment_method):
    """refund с частичной суммой → PARTIAL_REFUND."""
    from payments.services import PaymentService
    from payments.models import PaymentTransaction

    payment, _ = PaymentService.initiate_payment(order.id, payment_method.id)

    payload = {
        "payment_id": payment.acquiring_payment_id,
        "status": "completed",
        "transaction_id": "txn_partial",
        "amount": "500.00",
    }
    PaymentService.process_webhook(payload)

    txn = PaymentService.refund(payment.id, amount=Decimal("100.00"))

    assert txn.transaction_type == PaymentTransaction.TransactionType.PARTIAL_REFUND
    assert txn.amount == Decimal("100.00")
