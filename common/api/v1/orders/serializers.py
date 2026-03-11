"""Serializers for Orders API."""

from rest_framework import serializers

from orders.models import Order, OrderItem, OrderStatus


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            'id', 'product', 'product_name', 'quantity',
            'price', 'subtotal', 'marking_code',
        )
        read_only_fields = ('id', 'price', 'subtotal', 'product_name')


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ('id', 'status', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'store', 'store_name', 'kiosk', 'customer',
            'status', 'status_display',
            'order_type', 'order_type_display',
            'delivery_address', 'delivery_status',
            'estimated_delivery_at', 'delivered_at',
            'delivery_cost', 'courier_comment',
            'total_amount', 'discount_amount', 'final_amount',
            'payment_method', 'completed_at',
            'created_at', 'updated_at',
            'items', 'status_history',
        )
        read_only_fields = (
            'id', 'store_name', 'status_display', 'order_type_display',
            'total_amount', 'discount_amount', 'final_amount',
            'created_at', 'updated_at',
        )


class CreateOrderSerializer(serializers.Serializer):
    store_id = serializers.UUIDField()
    order_type = serializers.ChoiceField(
        choices=Order.OrderType.choices,
        default=Order.OrderType.DELIVERY,
    )
    delivery_address_id = serializers.IntegerField(required=False, allow_null=True)
    courier_comment = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        order_type = attrs.get('order_type', Order.OrderType.DELIVERY)
        delivery_address_id = attrs.get('delivery_address_id')
        if order_type == Order.OrderType.DELIVERY and not delivery_address_id:
            raise serializers.ValidationError(
                {'delivery_address_id': 'Адрес доставки обязателен для типа "доставка".'}
            )
        return attrs


class AddItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
