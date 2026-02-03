from decimal import Decimal
from typing import Any

from rest_framework import serializers


class NullableGeoFloatField(serializers.Field):
    """Координата: принимает число/строку, возвращает float или None (пустая строка → None)."""

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
    """Параметры запроса подсказок адресов Dadata (API v1)."""

    query = serializers.CharField(max_length=255)
    count = serializers.IntegerField(min_value=1, max_value=20, default=10, required=False)


class DadataSuggestionDataOutputSerializer(serializers.Serializer):
    """
    Канонический формат данных одного элемента подсказки Dadata (поля city, street, house, apartment, latitude, longitude).
    Используется в API и в админ-виджете (через DadataSuggestionNormalizerSerializer).
    Вход: словарь из Dadata с ключами flat, geo_lat, geo_lon и т.д. (вложенный data).
    """

    city = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    street = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    house = serializers.CharField(allow_blank=True, allow_null=True, default=None)
    apartment = serializers.CharField(source="flat", allow_blank=True, allow_null=True, default=None)
    latitude = NullableGeoFloatField(source="geo_lat", allow_null=True, default=None)
    longitude = NullableGeoFloatField(source="geo_lon", allow_null=True, default=None)


class DadataSuggestionNormalizerSerializer(serializers.Serializer):
    """Нормализует один элемент ответа Dadata suggest в формат для виджета адреса."""

    value = serializers.CharField(default="")
    data = DadataSuggestionDataOutputSerializer(default=None)


class AddressFromDadataSerializer(serializers.Serializer):
    """Валидация тела запроса «создать адрес из выбранной подсказки Dadata»."""

    city = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)
    street = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)
    house = serializers.CharField(max_length=50, allow_blank=False, trim_whitespace=True)
    apartment = serializers.CharField(max_length=50, allow_blank=True, allow_null=True, default=None, trim_whitespace=True)
    latitude = NullableGeoFloatField(allow_null=True, required=False, default=None)
    longitude = NullableGeoFloatField(allow_null=True, required=False, default=None)
