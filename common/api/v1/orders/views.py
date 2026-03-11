"""Views for Orders API."""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem
from orders.services.order_service import OrderService
from .serializers import (
    OrderSerializer,
    CreateOrderSerializer,
    AddItemSerializer,
)

logger = logging.getLogger(__name__)


class OrdersPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderListCreateView(APIView):
    """
    GET  /api/v1/orders/   — list own orders
    POST /api/v1/orders/   — create order
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            Order.objects.filter(customer=request.user)
            .prefetch_related('items__product', 'status_history')
            .order_by('-created_at')
        )
        paginator = OrdersPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            order = OrderService.create_order(
                user=request.user,
                store_id=data['store_id'],
                order_type=data['order_type'],
                delivery_address_id=data.get('delivery_address_id'),
                courier_comment=data.get('courier_comment', ''),
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    """
    GET /api/v1/orders/{id}/   — retrieve own order
    """
    permission_classes = [IsAuthenticated]

    def _get_order(self, request, order_id):
        return get_object_or_404(
            Order.objects.prefetch_related('items__product', 'status_history'),
            pk=order_id,
            customer=request.user,
        )

    def get(self, request, order_id):
        order = self._get_order(request, order_id)
        return Response(OrderSerializer(order).data)


class OrderItemsView(APIView):
    """
    POST /api/v1/orders/{id}/items/   — add item
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        get_object_or_404(Order, pk=order_id, customer=request.user)
        serializer = AddItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            item = OrderService.add_item(
                order_id=order_id,
                product_id=data['product_id'],
                quantity=data['quantity'],
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        from .serializers import OrderItemSerializer
        return Response(OrderItemSerializer(item).data, status=status.HTTP_201_CREATED)


class OrderItemDetailView(APIView):
    """
    DELETE /api/v1/orders/{id}/items/{item_id}/   — remove item
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, order_id, item_id):
        get_object_or_404(Order, pk=order_id, customer=request.user)
        try:
            OrderService.remove_item(order_id=order_id, item_id=item_id)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderSubmitView(APIView):
    """
    POST /api/v1/orders/{id}/submit/   — submit order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        get_object_or_404(Order, pk=order_id, customer=request.user)
        try:
            order = OrderService.submit_order(order_id=order_id)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)


class OrderCancelView(APIView):
    """
    POST /api/v1/orders/{id}/cancel/   — cancel order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        get_object_or_404(Order, pk=order_id, customer=request.user)
        try:
            order = OrderService.cancel_order(order_id=order_id)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)


class OrderTrackingView(APIView):
    """
    GET /api/v1/orders/{id}/tracking/

    Returns delivery tracking info:
    {current_status, estimated_delivery_at, delivered_at, history: [...]}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        from orders.models import OrderStatusLog

        order = get_object_or_404(
            Order.objects.prefetch_related('status_logs'),
            pk=order_id,
            customer=request.user,
        )
        logs = order.status_logs.order_by('created_at')
        history = [
            {
                'status': log.status,
                'comment': log.comment,
                'created_at': log.created_at,
            }
            for log in logs
        ]
        return Response({
            'current_status': order.status,
            'estimated_delivery_at': order.estimated_delivery_at,
            'delivered_at': order.delivered_at,
            'history': history,
        })
