"""Сериализаторы для фискального API."""

from rest_framework import serializers

from fiscal.models import OFDResponse, Receipt, ReceiptItem, ReceiptStatus


class ReceiptItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptItem
        fields = ('id', 'product_name', 'quantity', 'price', 'total', 'tax_rate', 'tax_amount')


class ReceiptStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptStatus
        fields = ('id', 'status', 'changed_at', 'comment')


class OFDResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OFDResponse
        fields = ('id', 'status_code', 'response_data', 'error_message', 'created_at')


class ReceiptSerializer(serializers.ModelSerializer):
    items = ReceiptItemSerializer(many=True, read_only=True)
    status_history = ReceiptStatusSerializer(many=True, read_only=True)
    ofd_responses = OFDResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Receipt
        fields = (
            'id',
            'order',
            'receipt_number',
            'status',
            'fiscal_data',
            'ofd_response',
            'sent_at',
            'confirmed_at',
            'error_message',
            'created_at',
            'updated_at',
            'items',
            'status_history',
            'ofd_responses',
        )
        read_only_fields = fields


class OFDWebhookSerializer(serializers.Serializer):
    """Сериализатор входящего webhook-запроса от ОФД."""

    receipt_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=['confirmed', 'failed'])
    response_data = serializers.DictField(required=False, default=dict)
    error_message = serializers.CharField(required=False, allow_blank=True, default='')
    status_code = serializers.IntegerField(required=False, allow_null=True, default=None)
