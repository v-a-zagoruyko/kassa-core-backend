"""Views для фискального API."""

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscal.models import Receipt
from fiscal.services import ReceiptService
from fiscal.tasks import send_receipt_to_ofd
from .permissions import IsAdminOrManager
from .serializers import OFDWebhookSerializer, ReceiptSerializer

logger = logging.getLogger(__name__)


class ReceiptsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

class OFDWebhookView(APIView):
    """
    POST /api/v1/integrations/ofd/webhook/

    Принимает уведомление от ОФД о статусе чека.
    Аутентификация по заголовку X-OFD-Token.
    """
    authentication_classes = []
    permission_classes = []

    def _check_token(self, request):
        expected = getattr(settings, 'OFD_WEBHOOK_TOKEN', '')
        if not expected:
            return True
        return request.headers.get('X-OFD-Token', '') == expected

    def post(self, request):
        if not self._check_token(request):
            return Response({'detail': 'Неверный токен.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = OFDWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            ReceiptService.handle_ofd_response(
                receipt_id=data['receipt_id'],
                response={
                    'status': data['status'],
                    'response_data': data['response_data'],
                    'error_message': data['error_message'],
                    'status_code': data['status_code'],
                },
            )
        except Receipt.DoesNotExist:
            return Response({'detail': 'Чек не найден.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.exception('Ошибка обработки webhook ОФД: %s', exc)
            return Response({'detail': 'Внутренняя ошибка.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'status': 'ok'})


# ---------------------------------------------------------------------------
# Admin API
# ---------------------------------------------------------------------------

class AdminReceiptListView(APIView):
    """
    GET /api/v1/admin/fiscal/receipts/

    Список чеков с фильтрацией по status, order_id, date_from, date_to.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        qs = Receipt.objects.prefetch_related('items', 'status_history', 'ofd_responses').order_by('-created_at')

        receipt_status = request.query_params.get('status')
        if receipt_status:
            qs = qs.filter(status=receipt_status)

        order_id = request.query_params.get('order_id')
        if order_id:
            qs = qs.filter(order_id=order_id)

        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        paginator = ReceiptsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ReceiptSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminReceiptDetailView(APIView):
    """
    GET /api/v1/admin/fiscal/receipts/{id}/

    Детали конкретного чека.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, receipt_id):
        receipt = get_object_or_404(
            Receipt.objects.prefetch_related('items', 'status_history', 'ofd_responses'),
            pk=receipt_id,
        )
        return Response(ReceiptSerializer(receipt).data)


class AdminReceiptGenerateView(APIView):
    """
    POST /api/v1/admin/fiscal/receipts/{order_id}/generate/

    Вручную генерирует чек для оплаченного заказа, если он ещё не создан.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request, order_id):
        try:
            receipt = ReceiptService.generate_receipt(order_id=order_id)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception('Ошибка генерации чека для заказа %s: %s', order_id, exc)
            return Response({'detail': 'Внутренняя ошибка.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(ReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


class AdminReceiptSendView(APIView):
    """
    POST /api/v1/admin/fiscal/receipts/{id}/send/

    Вручную запускает отправку чека в ОФД через Celery.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request, receipt_id):
        receipt = get_object_or_404(Receipt, pk=receipt_id)
        send_receipt_to_ofd.delay(str(receipt.id))
        return Response({'status': 'queued', 'receipt_id': str(receipt.id)})
