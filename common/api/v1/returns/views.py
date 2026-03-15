import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from returns.models import Return
from returns.services import ReturnService
from .permissions import IsAdminOrManager
from .serializers import CreateReturnSerializer, ReturnSerializer

logger = logging.getLogger(__name__)


class ReturnsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminReturnListView(APIView):
    """
    GET  /api/v1/admin/returns/   — список возвратов (filter: order_id, status)
    POST /api/v1/admin/returns/   — создать возврат
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        qs = Return.objects.prefetch_related('items', 'status_history').select_related(
            'order', 'processed_by', 'reason'
        ).order_by('-created_at')

        order_id = request.query_params.get('order_id')
        if order_id:
            qs = qs.filter(order_id=order_id)

        ret_status = request.query_params.get('status')
        if ret_status:
            qs = qs.filter(status=ret_status)

        paginator = ReturnsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ReturnSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateReturnSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            ret = ReturnService.create_return(
                order_id=data['order_id'],
                items=[
                    {
                        'order_item_id': item['order_item_id'],
                        'quantity': item['quantity'],
                        'refund_amount': item['refund_amount'],
                    }
                    for item in data['items']
                ],
                processed_by_user_id=request.user.pk,
                refund_method=data['refund_method'],
                reason_id=data.get('reason_id'),
                comment=data.get('comment', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception('Ошибка создания возврата: %s', exc)
            return Response({'detail': 'Внутренняя ошибка.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(ReturnSerializer(ret).data, status=status.HTTP_201_CREATED)


class AdminReturnDetailView(APIView):
    """GET /api/v1/admin/returns/{id}/ — детали возврата."""
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, return_id):
        ret = get_object_or_404(
            Return.objects.prefetch_related('items', 'status_history').select_related(
                'order', 'processed_by', 'reason'
            ),
            pk=return_id,
        )
        return Response(ReturnSerializer(ret).data)


class AdminReturnProcessView(APIView):
    """POST /api/v1/admin/returns/{id}/process/ — обработать возврат."""
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request, return_id):
        try:
            ret = ReturnService.process_refund(return_id=return_id)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception('Ошибка обработки возврата %s: %s', return_id, exc)
            return Response({'detail': 'Внутренняя ошибка.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(ReturnSerializer(ret).data)
