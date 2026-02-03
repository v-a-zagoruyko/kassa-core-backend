"""Тесты админ-views виджета адреса (Dadata подсказки, координаты, создание адреса)."""

import json
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from stores import admin_views


@pytest.fixture
def request_factory():
    return RequestFactory()


class TestDadataAddressSuggestView:
    def test_get_with_short_query_returns_empty_list(self, request_factory):
        request = request_factory.get("/admin/stores/store/dadata-suggest/", {"query": "а"})
        response = admin_views.dadata_address_suggest_view(request)
        assert response.status_code == 200
        assert json.loads(response.content) == []

    def test_get_with_empty_query_returns_empty_list(self, request_factory):
        request = request_factory.get("/admin/stores/store/dadata-suggest/", {"query": ""})
        response = admin_views.dadata_address_suggest_view(request)
        assert response.status_code == 200
        assert json.loads(response.content) == []

    def test_get_with_valid_query_returns_normalized_suggestions(self, request_factory):
        raw_suggestions = [
            {
                "value": "г Москва, ул Грибоедова, д 1",
                "data": {
                    "city": "Москва",
                    "street": "Грибоедова",
                    "house": "1",
                    "flat": "5",
                    "geo_lat": "55.75",
                    "geo_lon": "37.62",
                },
            },
        ]
        with patch.object(admin_views, "DadataService") as MockDadataService:
            MockDadataService.return_value.suggest_addresses.return_value = raw_suggestions
            request = request_factory.get(
                "/admin/stores/store/dadata-suggest/",
                {"query": "грибоедова"},
            )
            response = admin_views.dadata_address_suggest_view(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data) == 1
        assert data[0]["value"] == "г Москва, ул Грибоедова, д 1"
        assert data[0]["data"]["city"] == "Москва"
        assert data[0]["data"]["street"] == "Грибоедова"
        assert data[0]["data"]["house"] == "1"
        assert data[0]["data"]["apartment"] == "5"
        assert data[0]["data"]["latitude"] == 55.75
        assert data[0]["data"]["longitude"] == 37.62

    def test_get_when_dadata_raises_returns_502_suggest_failed(self, request_factory):
        with patch.object(admin_views, "DadataService") as MockDadataService:
            MockDadataService.return_value.suggest_addresses.side_effect = Exception(
                "Dadata unavailable"
            )
            request = request_factory.get(
                "/admin/stores/store/dadata-suggest/",
                {"query": "москва"},
            )
            response = admin_views.dadata_address_suggest_view(request)

        assert response.status_code == 502
        data = json.loads(response.content)
        assert data["error"] == "suggest_failed"
        assert "message" in data

    def test_post_returns_405(self, request_factory):
        request = request_factory.post("/admin/stores/store/dadata-suggest/", {"query": "москва"})
        response = admin_views.dadata_address_suggest_view(request)
        assert response.status_code == 405
        data = json.loads(response.content)
        assert data["error"] == "method_not_allowed"
