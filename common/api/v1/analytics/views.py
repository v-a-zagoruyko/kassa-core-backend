"""Views аналитического API (только admin/manager/root)."""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import Dashboard, Report
from analytics.services import AnalyticsService
from common.api.v1.fiscal.permissions import IsAdminOrManager

from .serializers import (
    CreateDashboardSerializer,
    DashboardSerializer,
    GenerateReportSerializer,
    MetricSerializer,
    ReportSerializer,
)

logger = logging.getLogger(__name__)


class AnalyticsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class AnalyticsMetricsView(APIView):
    """
    GET /api/v1/admin/analytics/metrics/

    Параметры: store_id?, date_from, date_to, metric_types? (через запятую)
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        store_id = request.query_params.get('store_id') or None
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if not date_from or not date_to:
            return Response(
                {'detail': 'date_from и date_to обязательны.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metric_types_param = request.query_params.get('metric_types')
        metric_types = metric_types_param.split(',') if metric_types_param else None

        try:
            qs = AnalyticsService.get_metrics(store_id, date_from, date_to, metric_types)
        except Exception as exc:
            logger.exception('Ошибка получения метрик: %s', exc)
            return Response({'detail': 'Внутренняя ошибка.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        paginator = AnalyticsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = MetricSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class AnalyticsReportListCreateView(APIView):
    """
    GET  /api/v1/admin/analytics/reports/ — список отчётов
    POST /api/v1/admin/analytics/reports/ — генерация отчёта
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        qs = Report.objects.select_related('store', 'created_by').order_by('-created_at')

        store_id = request.query_params.get('store_id')
        if store_id:
            qs = qs.filter(store_id=store_id)

        paginator = AnalyticsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ReportSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            report = AnalyticsService.generate_report(
                report_type=data['report_type'],
                store_id=data.get('store_id'),
                date_from=data['date_from'],
                date_to=data['date_to'],
                format=data['format'],
                user_id=request.user.id,
            )
        except Exception as exc:
            logger.exception('Ошибка генерации отчёта: %s', exc)
            return Response({'detail': 'Внутренняя ошибка.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class AnalyticsReportDetailView(APIView):
    """GET /api/v1/admin/analytics/reports/{id}/"""
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request, report_id):
        report = get_object_or_404(Report.objects.select_related('store', 'created_by'), pk=report_id)
        return Response(ReportSerializer(report).data)


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

class AnalyticsDashboardListCreateView(APIView):
    """
    GET  /api/v1/admin/analytics/dashboards/ — дашборды текущего пользователя
    POST /api/v1/admin/analytics/dashboards/ — создать дашборд
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get(self, request):
        qs = AnalyticsService.get_user_dashboards(request.user.id)
        paginator = AnalyticsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = DashboardSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateDashboardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        dashboard = Dashboard.objects.create(
            name=data['name'],
            config=data.get('config', {}),
            is_active=data.get('is_active', True),
            user=request.user,
        )
        return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)
