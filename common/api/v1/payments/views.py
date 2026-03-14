"""API views для платёжного модуля."""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api.v1.payments.serializers import (
    InitiatePaymentSerializer,
    PaymentMethodSerializer,
    PaymentSerializer,
)
from orders.models import Order
from payments.models import Payment, PaymentMethod
from payments.services import PaymentService


class OrderPayView(APIView):
    """
    POST /api/v1/orders/{id}/pay/
    Инициировать оплату заказа.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Заказ не найден."}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что заказ принадлежит пользователю
        if order.customer != request.user:
            return Response(
                {"detail": "Нет доступа к этому заказу."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Заказ должен быть в статусе pending или pending_payment
        if order.status not in (Order.Status.PENDING, Order.Status.PENDING_PAYMENT):
            return Response(
                {"detail": f"Оплата невозможна для заказа со статусом '{order.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method_id = serializer.validated_data["payment_method_id"]

        try:
            payment, payment_url = PaymentService.initiate_payment(order_id, payment_method_id)
        except PaymentMethod.DoesNotExist:
            return Response(
                {"detail": "Метод оплаты не найден."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "payment_id": payment.id,
                "payment_url": payment_url,
                "status": payment.status,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/payments/{id}/
    Детали платежа (только свои).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(
            order__customer=self.request.user
        ).select_related("method", "order")

    def get_object(self):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(self.get_queryset(), id=self.kwargs["payment_id"])


class PaymentMethodListView(generics.ListAPIView):
    """
    GET /api/v1/payments/methods/
    Список активных методов оплаты.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(is_active=True)


class PaymentWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/

    Публичный endpoint (без JWT — вызывает эквайер).
    Принимает сырой payload от эквайера и обрабатывает его через PaymentService.

    ВАЖНО: В реальной интеграции здесь должна быть верификация подписи
    (HMAC или подпись эквайера), чтобы исключить подделку запросов.
    Текущая заглушка принимает все запросы без проверки.
    """

    permission_classes = []  # Публичный endpoint

    def post(self, request):
        payload = request.data

        if not payload:
            return Response(
                {"detail": "Пустой payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = PaymentService.process_webhook(payload)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Платёж не найден."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Webhook processing error: %s", exc)
            return Response(
                {"detail": "Ошибка обработки webhook."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"status": "ok", "payment_status": payment.status},
            status=status.HTTP_200_OK,
        )
