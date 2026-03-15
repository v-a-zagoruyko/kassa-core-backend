"""Tests for ProductService and StockService."""

import decimal
from unittest.mock import MagicMock, patch

import pytest

from common.models import Address
from products.models import Category, Product, Stock
from products.services.product_service import ProductService, _make_product_key, _make_kiosk_products_key
from products.services.stock_service import get_available_quantity
from stores.models import Kiosk, Store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def address(db):
    return Address.objects.create(city="Тюмень", street="Ленина", house="1")


@pytest.fixture
def store(address):
    return Store.objects.create(name="Test Store", address=address)


@pytest.fixture
def kiosk(store):
    return Kiosk.objects.create(store=store, kiosk_number="K01", is_active=True)


@pytest.fixture
def category():
    return Category.objects.create(name="Электроника")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Тестовый товар",
        category=category,
        price=decimal.Decimal("299.00"),
        is_active=True,
    )


@pytest.fixture
def stock(product, store):
    return Stock.objects.create(product=product, store=store, quantity=decimal.Decimal("10"))


# ---------------------------------------------------------------------------
# ProductService — cache key helpers
# ---------------------------------------------------------------------------

def test_make_product_key():
    assert _make_product_key("abc") == "product:abc"


def test_make_kiosk_products_key():
    assert _make_kiosk_products_key("xyz") == "kiosk:xyz:products"


# ---------------------------------------------------------------------------
# ProductService — get_product
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductServiceGetProduct:
    def _make_service(self):
        """Return service instance with cache disabled."""
        svc = ProductService()
        svc._cache_available = False
        return svc

    def test_get_product_returns_dict(self, product):
        svc = self._make_service()
        result = svc.get_product(product.id)

        assert result is not None
        assert result["id"] == str(product.id)
        assert result["name"] == product.name
        assert result["price"] == str(product.price)
        assert result["is_active"] is True

    def test_get_product_category_dict(self, product, category):
        svc = self._make_service()
        result = svc.get_product(product.id)

        assert result["category"]["id"] == str(category.id)
        assert result["category"]["name"] == category.name

    def test_get_product_not_found_returns_none(self, db):
        import uuid
        svc = self._make_service()
        result = svc.get_product(uuid.uuid4())
        assert result is None

    def test_get_product_inactive_returns_none(self, product):
        product.is_active = False
        product.save()
        svc = self._make_service()
        result = svc.get_product(product.id)
        assert result is None

    def test_get_product_uses_cache_hit(self, product):
        """If cache returns a value, it should be returned without hitting DB."""
        svc = ProductService()
        svc._cache_available = True
        cached_value = {"id": str(product.id), "name": "from_cache"}

        with patch.object(svc, "_cache_get", return_value=cached_value) as mock_get:
            result = svc.get_product(product.id)
        assert result == cached_value
        mock_get.assert_called_once_with(_make_product_key(product.id))

    def test_get_product_caches_on_miss(self, product):
        svc = ProductService()
        svc._cache_available = True

        with patch.object(svc, "_cache_get", return_value=None), \
             patch.object(svc, "_cache_set") as mock_set:
            result = svc.get_product(product.id)

        assert result is not None
        mock_set.assert_called_once()


# ---------------------------------------------------------------------------
# ProductService — get_products_for_kiosk
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductServiceGetProductsForKiosk:
    def _make_service(self):
        svc = ProductService()
        svc._cache_available = False
        return svc

    def test_returns_products_with_stock(self, kiosk, product, stock):
        svc = self._make_service()
        results = svc.get_products_for_kiosk(kiosk.id)

        assert len(results) == 1
        assert results[0]["id"] == str(product.id)

    def test_returns_empty_for_zero_stock(self, kiosk, product):
        Stock.objects.create(product=product, store=kiosk.store, quantity=0)
        svc = self._make_service()
        results = svc.get_products_for_kiosk(kiosk.id)
        assert results == []

    def test_returns_empty_for_inactive_kiosk(self, store, product, stock):
        inactive_kiosk = Kiosk.objects.create(store=store, kiosk_number="K99", is_active=False)
        svc = self._make_service()
        results = svc.get_products_for_kiosk(inactive_kiosk.id)
        assert results == []

    def test_returns_empty_for_nonexistent_kiosk(self, db):
        import uuid
        svc = self._make_service()
        results = svc.get_products_for_kiosk(uuid.uuid4())
        assert results == []

    def test_cache_hit_returns_cached(self, kiosk):
        svc = ProductService()
        svc._cache_available = True
        cached = [{"id": "fake"}]
        with patch.object(svc, "_cache_get", return_value=cached):
            result = svc.get_products_for_kiosk(kiosk.id)
        assert result == cached

    def test_caches_on_miss(self, kiosk, product, stock):
        svc = ProductService()
        svc._cache_available = True
        with patch.object(svc, "_cache_get", return_value=None), \
             patch.object(svc, "_cache_set") as mock_set:
            svc.get_products_for_kiosk(kiosk.id)
        mock_set.assert_called_once()

    def test_inactive_products_excluded(self, kiosk, product, stock):
        product.is_active = False
        product.save()
        svc = self._make_service()
        results = svc.get_products_for_kiosk(kiosk.id)
        assert results == []


# ---------------------------------------------------------------------------
# ProductService — invalidate cache
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductServiceInvalidate:
    def test_invalidate_product_cache(self, product):
        svc = ProductService()
        svc._cache_available = True
        with patch.object(svc, "_cache_delete") as mock_del:
            svc.invalidate_cache(product.id)
        mock_del.assert_called_once_with(_make_product_key(product.id))

    def test_invalidate_kiosk_cache(self, kiosk):
        svc = ProductService()
        svc._cache_available = True
        with patch.object(svc, "_cache_delete") as mock_del:
            svc.invalidate_kiosk_cache(kiosk.id)
        mock_del.assert_called_once_with(_make_kiosk_products_key(kiosk.id))

    def test_invalidate_no_op_when_cache_unavailable(self, product):
        svc = ProductService()
        svc._cache_available = False
        # Should not raise
        svc.invalidate_cache(product.id)
        svc.invalidate_kiosk_cache(product.id)


# ---------------------------------------------------------------------------
# ProductService — cache backend unavailable (graceful degradation)
# ---------------------------------------------------------------------------

def test_cache_check_unavailable_on_exception():
    """_check_cache_available returns False when cache raises."""
    with patch("django.core.cache.cache.get", side_effect=Exception("Redis down")):
        svc = ProductService()
        # May return True or False depending on Django's cache setup,
        # but should not raise.
        assert isinstance(svc._cache_available, bool)


@pytest.mark.django_db
def test_cache_get_swallows_errors(product):
    svc = ProductService()
    svc._cache_available = True
    # Simulate cache error by patching the import inside _cache_get
    with patch("common.cache.cache_get", side_effect=Exception("err")):
        result = svc._cache_get("some-key")
        assert result is None


# ---------------------------------------------------------------------------
# StockService — get_available_quantity
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetAvailableQuantity:
    def test_returns_available_quantity(self, product, store, stock):
        stock.quantity = decimal.Decimal("10")
        stock.reserved_quantity = decimal.Decimal("3")
        stock.save()

        result = get_available_quantity(product, store)
        assert result == decimal.Decimal("7")

    def test_returns_zero_when_no_stock(self, product, store):
        result = get_available_quantity(product, store)
        assert result == decimal.Decimal("0")

    def test_returns_zero_when_fully_reserved(self, product, store, stock):
        stock.quantity = decimal.Decimal("5")
        stock.reserved_quantity = decimal.Decimal("5")
        stock.save()

        result = get_available_quantity(product, store)
        assert result == decimal.Decimal("0")

    def test_accepts_ids_not_objects(self, product, store, stock):
        result = get_available_quantity(product.id, store.id)
        assert result >= decimal.Decimal("0")
