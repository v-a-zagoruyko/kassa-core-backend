from rest_framework import serializers

from returns.models import Return, ReturnItem, ReturnReason, ReturnStatus


class ReturnReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnReason
        fields = ('id', 'code', 'name', 'description', 'is_active')


class ReturnItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnItem
        fields = ('id', 'order_item', 'quantity', 'refund_amount')


class ReturnStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnStatus
        fields = ('id', 'status', 'changed_at', 'changed_by', 'comment')


class ReturnSerializer(serializers.ModelSerializer):
    items = ReturnItemSerializer(many=True, read_only=True)
    status_history = ReturnStatusSerializer(many=True, read_only=True)

    class Meta:
        model = Return
        fields = (
            'id',
            'order',
            'processed_by',
            'status',
            'total_amount',
            'refund_method',
            'refund_status',
            'reason',
            'comment',
            'completed_at',
            'created_at',
            'updated_at',
            'items',
            'status_history',
        )
        read_only_fields = fields


class ReturnItemInputSerializer(serializers.Serializer):
    order_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class CreateReturnSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    items = ReturnItemInputSerializer(many=True, min_length=1)
    refund_method = serializers.ChoiceField(choices=Return.RefundMethod.choices)
    reason_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    comment = serializers.CharField(required=False, allow_blank=True, default='')
