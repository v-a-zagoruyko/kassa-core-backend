from rest_framework import serializers

from stores.models import DeliveryZone


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = (
            'id', 'store', 'name', 'radius_km',
            'min_order_amount', 'delivery_cost',
            'delivery_time_minutes', 'is_active',
        )
        read_only_fields = ('id',)


class DeliveryCheckSerializer(serializers.Serializer):
    store_id = serializers.UUIDField()
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lon = serializers.DecimalField(max_digits=9, decimal_places=6)


class DeliveryCheckResponseSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    delivery_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    estimated_minutes = serializers.IntegerField()
    min_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
