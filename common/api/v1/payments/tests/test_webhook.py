"""
Тесты Webhook endpoint.
"""
import pytest
from decimal import Decimal
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


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
        final_amount=Decimal("300.00"),
    )


@pytest.fixture
def order_item(db, order, product):
    from orders.models import OrderItem
    return OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=Decimal("150.00"),
        subtotal=Decimal("300.00"),
    )


@pytest.fixture
def payment_method(db):
    from payments.models import PaymentMethod
    return PaymentMethod.objects.create(name="card", display_name="Карта", is_active=True)


@pytest.fixture
def payment(db, order, payment_method):
    """Платёж в статусе processing с mock acquiring_payment_id."""
    from payments.models import Payment
    return Payment.objects.create(
        order=order,
        amount=Decimal("300.00"),
        method=payment_method,
        status=Payment.Status.PROCESSING,
        acquiring_payment_id="mock_test001",
    )


WEBHOOK_URL = "/api/v1/payments/webhook/"


@pytest.mark.django_db(transaction=True)
def test_webhook_completed(api_client, payment, order, order_item, stock):
    """Webhook completed → Payment completed, Order PAID."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation

    # Создаём резерв
    ReservationService.reserve_products(order.id)

    payload = {
        "payment_id": "mock_test001",
        "status": "completed",
        "transaction_id": "txn_webhook_001",
        "amount": "300.00",
    }
    response = api_client.post(WEBHOOK_URL, payload, format="json")

    assert response.status_code == 200, response.data
    assert response.data["status"] == "ok"
    assert response.data["payment_status"] == "completed"

    payment.refresh_from_db()
    from payments.models import Payment
    assert payment.status == Payment.Status.COMPLETED

    order.refresh_from_db()
    from orders.models import Order
    assert order.status == Order.Status.PAID

    # Резервы завершены
    reservations = Reservation.objects.filter(order=order)
    for r in reservations:
        assert r.status == Reservation.Status.COMPLETED


@pytest.mark.django_db(transaction=True)
def test_webhook_failed(api_client, payment, order, order_item, stock):
    """Webhook failed → Payment failed, Order CANCELLED, резервы освобождены."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation

    # Создаём резерв
    ReservationService.reserve_products(order.id)

    payload = {
        "payment_id": "mock_test001",
        "status": "failed",
        "transaction_id": "txn_webhook_fail",
        "amount": "300.00",
        "failure_reason": "Insufficient funds",
    }
    response = api_client.post(WEBHOOK_URL, payload, format="json")

    assert response.status_code == 200, response.data
    assert response.data["payment_status"] == "failed"

    payment.refresh_from_db()
    from payments.models import Payment
    assert payment.status == Payment.Status.FAILED
    assert payment.failure_reason == "Insufficient funds"

    order.refresh_from_db()
    from orders.models import Order
    assert order.status == Order.Status.CANCELLED

    # Резервы освобождены
    reservations = Reservation.objects.filter(order=order)
    for r in reservations:
        assert r.status == Reservation.Status.RELEASED


@pytest.mark.django_db
def test_webhook_unknown_payment(api_client):
    """Webhook с неизвестным payment_id → 400."""
    payload = {
        "payment_id": "unknown_id_xyz",
        "status": "completed",
        "transaction_id": "txn_xxx",
        "amount": "100.00",
    }
    response = api_client.post(WEBHOOK_URL, payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_webhook_empty_payload(api_client):
    """Пустой payload → 400."""
    response = api_client.post(WEBHOOK_URL, {}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_webhook_no_auth_required(api_client, payment):
    """Webhook доступен без JWT."""
    payload = {
        "payment_id": "mock_test001",
        "status": "completed",
        "transaction_id": "txn_noauth",
        "amount": "300.00",
    }
    # Нет Authorization заголовка — должно работать
    response = api_client.post(WEBHOOK_URL, payload, format="json")
    assert response.status_code == 200
