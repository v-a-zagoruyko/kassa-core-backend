from typing import Any, Dict

from rest_framework import serializers


class DadataAddressSuggestRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=255)
    count = serializers.IntegerField(min_value=1, max_value=20, default=10, required=False)


class DadataAddressSuggestionSerializer(serializers.Serializer):
    city = serializers.CharField(source="data.city", allow_null=True, required=False)
    street = serializers.CharField(source="data.street", allow_null=True, required=False)
    house = serializers.CharField(source="data.house", allow_null=True, required=False)
    apartment = serializers.CharField(source="data.flat", allow_null=True, required=False)
    latitude = serializers.FloatField(source="data.geo_lat", allow_null=True, required=False)
    longitude = serializers.FloatField(source="data.geo_lon", allow_null=True, required=False)
