"""Тесты сериализаторов Dadata (API v1 и виджет)."""

from common.api.v1.common.serializers import (
    DadataAddressSuggestionSerializer,
    DadataSuggestionNormalizerSerializer,
)


class TestDadataAddressSuggestionSerializer:
    def test_serializes_full_suggestion_to_flat_format(self):
        raw = {
            "value": "г Москва, ул Грибоедова, д 1",
            "data": {
                "city": "Москва",
                "street": "Грибоедова",
                "house": "1",
                "flat": "5",
                "geo_lat": "55.75",
                "geo_lon": "37.62",
            },
        }
        serializer = DadataAddressSuggestionSerializer(instance=raw)
        data = serializer.data
        assert data["value"] == "г Москва, ул Грибоедова, д 1"
        assert data["city"] == "Москва"
        assert data["street"] == "Грибоедова"
        assert data["house"] == "1"
        assert data["apartment"] == "5"
        assert data["latitude"] == 55.75
        assert data["longitude"] == 37.62


class TestDadataSuggestionNormalizerSerializer:
    def test_serializes_raw_dadata_item_to_value_and_data(self):
        raw = {
            "value": "г Москва, ул Грибоедова, д 1",
            "data": {
                "city": "Москва",
                "street": "Грибоедова",
                "house": "1",
                "flat": "5",
                "geo_lat": "55.75",
                "geo_lon": "37.62",
            },
        }
        serializer = DadataSuggestionNormalizerSerializer(instance=raw)
        data = serializer.data
        assert data["value"] == "г Москва, ул Грибоедова, д 1"
        assert data["data"]["city"] == "Москва"
        assert data["data"]["street"] == "Грибоедова"
        assert data["data"]["house"] == "1"
        assert data["data"]["apartment"] == "5"
        assert data["data"]["latitude"] == 55.75
        assert data["data"]["longitude"] == 37.62

    def test_accepts_empty_data(self):
        raw = {"value": "адрес", "data": None}
        serializer = DadataSuggestionNormalizerSerializer(instance=raw)
        data = serializer.data
        assert data["value"] == "адрес"
        assert data["data"] is None
