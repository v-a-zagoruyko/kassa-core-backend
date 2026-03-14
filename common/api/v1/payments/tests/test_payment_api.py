"""
Тесты Payment API.
"""
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from django.urls import reverse


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
def user(db):
    from accounts.models import User
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def other_user(db):
    from accounts.models import User
    return User.objects.create_user(username="other", password="testpass123")


@pytest.fixture
def payment_method(db):
    from payments.models import PaymentMethod
    return PaymentMethod.objects.create(name="card", display_name="Карта", is_active=True)


@pytest.fixture
def inactive_payment_method(db):
    from payments.models import PaymentMethod
    return PaymentMethod.objects.create(name="cash", display_name="Наличные", is_active=False)


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
def auth_client(api_client, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/orders/{id}/pay/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_initiate_payment_success(auth_client, order, payment_method):
    """POST orders/{id}/pay/ → 201 с payment_id, payment_url, status."""
    url = f"/api/v1/orders/{order.id}/pay/"
    response = auth_client.post(url, {"payment_method_id": str(payment_method.id)}, format="json")

    assert response.status_code == 201, response.data
    assert "payment_id" in response.data
    assert "payment_url" in response.data
    assert response.data["status"] == "processing"


@pytest.mark.django_db
def test_initiate_payment_requires_auth(api_client, order, payment_method):
    """Без JWT → 401."""
    url = f"/api/v1/orders/{order.id}/pay/"
    response = api_client.post(url, {"payment_method_id": str(payment_method.id)}, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_initiate_payment_wrong_user(api_client, other_user, order, payment_method):
    """Чужой заказ → 403."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    url = f"/api/v1/orders/{order.id}/pay/"
    response = api_client.post(url, {"payment_method_id": str(payment_method.id)}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_initiate_payment_not_found(auth_client, payment_method):
    """Несуществующий заказ → 404."""
    import uuid
    url = f"/api/v1/orders/{uuid.uuid4()}/pay/"
    response = auth_client.post(url, {"payment_method_id": str(payment_method.id)}, format="json")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/payments/{id}/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_payment_detail(auth_client, order, payment_method):
    """GET payments/{id}/ → 200 с деталями."""
    from payments.models import Payment
    payment = Payment.objects.create(
        order=order,
        amount=Decimal("300.00"),
        method=payment_method,
    )
    url = f"/api/v1/payments/{payment.id}/"
    response = auth_client.get(url)
    assert response.status_code == 200
    assert str(response.data["id"]) == str(payment.id)
    assert response.data["status"] == "pending"


@pytest.mark.django_db
def test_get_payment_detail_other_user(api_client, other_user, order, payment_method):
    """Чужой платёж → 404 (не виден)."""
    from payments.models import Payment
    from rest_framework_simplejwt.tokens import RefreshToken

    payment = Payment.objects.create(
        order=order,
        amount=Decimal("300.00"),
        method=payment_method,
    )
    refresh = RefreshToken.for_user(other_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    url = f"/api/v1/payments/{payment.id}/"
    response = api_client.get(url)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/payments/methods/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_payment_methods_list(auth_client, payment_method, inactive_payment_method):
    """GET payments/methods/ → только активные методы."""
    url = "/api/v1/payments/methods/"
    response = auth_client.get(url)
    assert response.status_code == 200
    names = [m["name"] for m in response.data]
    assert "card" in names
    assert "cash" not in names  # inactive


@pytest.mark.django_db
def test_payment_methods_requires_auth(api_client):
    """Без JWT → 401."""
    url = "/api/v1/payments/methods/"
    response = api_client.get(url)
    assert response.status_code == 401
