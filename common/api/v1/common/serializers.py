from decimal import Decimal
from typing import Any

from rest_framework import serializers


class NullableGeoFloatField(serializers.Field):
    """Координата: число/строка → float или None."""

    default_error_messages = {"invalid": "Недопустимое значение координаты."}

    def to_representation(self, value: Any) -> float | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        try:
            return float(Decimal(str(value)))
        except (TypeError, ValueError):
            return None

    def to_internal_value(self, data: Any) -> float | None:
        return self.to_representation(data)


class DadataAddressSuggestRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=255)
    count = serializers.IntegerField(min_value=1, max_value=20, default=10, required=False)


class DadataSuggestionDataOutputSerializer(serializers.Serializer):
    """Вложенный data для виджета (один элемент подсказки)."""

    city = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    street = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    house = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    apartment = serializers.CharField(source="flat", allow_blank=True, allow_null=True, default=None)
    latitude = NullableGeoFloatField(source="geo_lat", allow_null=True, default=None)
    longitude = NullableGeoFloatField(source="geo_lon", allow_null=True, default=None)


class DadataSuggestionNormalizerSerializer(serializers.Serializer):
    """Формат для виджета: value + data (для дропдауна и POST create-address)."""

    value = serializers.CharField(default="")
    data = DadataSuggestionDataOutputSerializer(default=None)


class DadataAddressSuggestionSerializer(serializers.Serializer):
    """Плоский формат для API v1: value + поля из data."""

    value = serializers.CharField(default="")
    city = serializers.CharField(source="data.city", allow_blank=True, allow_null=True, default=None)
    street = serializers.CharField(source="data.street", allow_blank=True, allow_null=True, default=None)
    house = serializers.CharField(source="data.house", allow_blank=True, allow_null=True, default=None)
    apartment = serializers.CharField(source="data.flat", allow_blank=True, allow_null=True, default=None)
    latitude = NullableGeoFloatField(source="data.geo_lat", allow_null=True, default=None)
    longitude = NullableGeoFloatField(source="data.geo_lon", allow_null=True, default=None)


class AddressFromDadataSerializer(serializers.Serializer):
    """Валидация тела POST create-address из виджета."""

    city = serializers.CharField(max_length=255, trim_whitespace=True)
    street = serializers.CharField(max_length=255, trim_whitespace=True)
    house = serializers.CharField(max_length=50, trim_whitespace=True)
    apartment = serializers.CharField(max_length=50, allow_blank=True, allow_null=True, default=None, trim_whitespace=True)
    comment = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        required=False,
        default=None,
        trim_whitespace=True,
    )
    latitude = NullableGeoFloatField(allow_null=True, required=False, default=None)
    longitude = NullableGeoFloatField(allow_null=True, required=False, default=None)
