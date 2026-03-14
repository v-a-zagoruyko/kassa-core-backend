"""Сериализаторы для платёжного API."""

from rest_framework import serializers

from payments.models import Payment, PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "display_name", "is_active"]


class PaymentSerializer(serializers.ModelSerializer):
    method = PaymentMethodSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "amount",
            "currency",
            "method",
            "status",
            "acquiring_payment_id",
            "initiated_at",
            "completed_at",
            "failed_at",
            "failure_reason",
        ]
        read_only_fields = fields


class InitiatePaymentSerializer(serializers.Serializer):
    payment_method_id = serializers.UUIDField()


class InitiatePaymentResponseSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    payment_url = serializers.URLField()
    status = serializers.CharField()
