"""URL-маршруты аналитического API."""

from django.urls import path

from .views import (
    AnalyticsDashboardListCreateView,
    AnalyticsMetricsView,
    AnalyticsReportDetailView,
    AnalyticsReportListCreateView,
)

urlpatterns = [
    path('admin/analytics/metrics/', AnalyticsMetricsView.as_view(), name='admin-analytics-metrics'),
    path('admin/analytics/reports/', AnalyticsReportListCreateView.as_view(), name='admin-analytics-reports'),
    path('admin/analytics/reports/<uuid:report_id>/', AnalyticsReportDetailView.as_view(), name='admin-analytics-report-detail'),
    path('admin/analytics/dashboards/', AnalyticsDashboardListCreateView.as_view(), name='admin-analytics-dashboards'),
]
