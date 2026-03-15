"""Тесты заглушки WarehouseService."""

import pytest

from integrations.warehouse import WarehouseService


@pytest.fixture
def service():
    return WarehouseService()


def test_get_stock_returns_expected_structure(service):
    result = service.get_stock(product_id="p1", store_id="s1")
    assert result == {"quantity": 0, "reserved": 0}


def test_reserve_item_returns_true(service):
    assert service.reserve_item(product_id="p1", store_id="s1", quantity=3) is True


def test_release_item_returns_true(service):
    assert service.release_item(product_id="p1", store_id="s1", quantity=3) is True


def test_sync_inventory_returns_expected_structure(service):
    result = service.sync_inventory()
    assert result == {"synced": 0}


def test_sync_inventory_with_store_id(service):
    result = service.sync_inventory(store_id="s1")
    assert result == {"synced": 0}
