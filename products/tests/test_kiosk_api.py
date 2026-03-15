"""Tests for Kiosk product API: GET /api/v1/kiosk/products/."""

import decimal
import pytest

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from common.models import Address
from products.models import Barcode, Category, Product, Stock
from stores.models import Kiosk, Store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def address(db):
    return Address.objects.create(city="Тюмень", street="Ленина", house="1")


@pytest.fixture
def store(address):
    return Store.objects.create(name="KioskTestStore", address=address)


@pytest.fixture
def kiosk(store):
    return Kiosk.objects.create(store=store, kiosk_number="K01", is_active=True)


@pytest.fixture
def category():
    return Category.objects.create(name="Напитки")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Кола",
        category=category,
        price=decimal.Decimal("89.00"),
        is_active=True,
    )


@pytest.fixture
def stock(product, store):
    return Stock.objects.create(product=product, store=store, quantity=decimal.Decimal("20"))


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username="kioskuser", password="pass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# KioskProductsView
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestKioskProductsView:
    URL = "/api/v1/kiosk/products/"

    def test_requires_authentication(self, client):
        resp = client.get(self.URL, {"kiosk_id": "some-uuid"})
        assert resp.status_code == 401

    def test_missing_kiosk_id_returns_400(self, auth_client):
        resp = auth_client.get(self.URL)
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "MISSING_KIOSK_ID"

    def test_invalid_kiosk_id_returns_404(self, auth_client):
        import uuid
        resp = auth_client.get(self.URL, {"kiosk_id": str(uuid.uuid4())})
        assert resp.status_code == 404
        assert resp.data["error"]["code"] == "KIOSK_NOT_FOUND"

    def test_non_uuid_kiosk_id_returns_error(self, auth_client):
        resp = auth_client.get(self.URL, {"kiosk_id": "not-a-uuid"})
        assert resp.status_code in (400, 404)

    def test_inactive_kiosk_returns_404(self, auth_client, store):
        inactive = Kiosk.objects.create(store=store, kiosk_number="K99", is_active=False)
        resp = auth_client.get(self.URL, {"kiosk_id": str(inactive.id)})
        assert resp.status_code == 404

    def test_returns_products_with_stock(self, auth_client, kiosk, product, stock):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id)})
        assert resp.status_code == 200
        data = resp.data
        assert data["count"] == 1
        assert data["results"][0]["name"] == product.name

    def test_returns_empty_when_no_stock(self, auth_client, kiosk, product):
        # No stock record created
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id)})
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_filters_by_category_slug(self, auth_client, kiosk, product, stock, category):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id), "category": category.slug})
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_filters_by_nonexistent_category(self, auth_client, kiosk, product, stock):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id), "category": "no-such-slug"})
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_search_by_name(self, auth_client, kiosk, product, stock):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id), "search": "Кола"})
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_search_no_match(self, auth_client, kiosk, product, stock):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id), "search": "ЧегоНетТочно"})
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_search_by_barcode(self, auth_client, kiosk, product, stock):
        Barcode.objects.create(
            product=product, code="5901234123457", barcode_type=Barcode.BarcodeType.EAN_13
        )
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id), "search": "590123"})
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_inactive_products_excluded(self, auth_client, kiosk, product, stock):
        product.is_active = False
        product.save()
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id)})
        assert resp.status_code == 200
        assert resp.data["count"] == 0

    def test_response_contains_expected_fields(self, auth_client, kiosk, product, stock):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id)})
        item = resp.data["results"][0]
        assert "id" in item
        assert "name" in item
        assert "price" in item
        assert "category" in item
        assert "stock_quantity" in item

    def test_stock_quantity_in_response(self, auth_client, kiosk, product, stock):
        resp = auth_client.get(self.URL, {"kiosk_id": str(kiosk.id)})
        item = resp.data["results"][0]
        # stock.quantity=20, reserved_quantity=0 → available=20
        assert item["stock_quantity"] == 20.0
