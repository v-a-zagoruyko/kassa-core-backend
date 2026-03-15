"""Тесты заглушки ERPService."""

import pytest

from integrations.erp import ERPService


@pytest.fixture
def service():
    return ERPService()


def test_sync_products_returns_expected_structure(service):
    result = service.sync_products()
    assert result == {"synced": 0}


def test_sync_orders_returns_expected_structure(service):
    result = service.sync_orders()
    assert result == {"synced": 0}


def test_push_sales_returns_expected_structure(service):
    result = service.push_sales(date_from="2026-01-01", date_to="2026-01-31")
    assert result == {"pushed": 0}
