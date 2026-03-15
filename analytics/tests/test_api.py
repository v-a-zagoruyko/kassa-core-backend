"""Тесты API аналитики."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from analytics.models import Metric, Report


@pytest.mark.django_db
class TestAnalyticsMetricsAPI:
    URL = '/api/v1/admin/analytics/metrics/'

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.URL, {'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_returns_403(self, api_client, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='regular_api', password='pass')
        api_client.force_authenticate(user=user)
        response = api_client.get(self.URL, {'date_from': '2026-01-01', 'date_to': '2026-01-31'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_date_params_returns_400(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_metrics_in_range(self, api_client, admin_user, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE,
            store=store,
            date=date(2026, 1, 15),
            value=Decimal('999.00'),
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL, {
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
            'store_id': str(store.id),
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['metric_type'] == 'revenue'

    def test_filter_by_metric_types(self, api_client, admin_user, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE, store=store,
            date=date(2026, 4, 1), value=Decimal('100'),
        )
        Metric.objects.create(
            metric_type=Metric.MetricType.ORDERS_COUNT, store=store,
            date=date(2026, 4, 1), value=Decimal('5'),
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL, {
            'date_from': '2026-04-01',
            'date_to': '2026-04-30',
            'metric_types': 'revenue',
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestAnalyticsReportsAPI:
    LIST_URL = '/api/v1/admin/analytics/reports/'

    def test_list_requires_auth(self, api_client):
        response = api_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_returns_reports(self, api_client, admin_user, store):
        Report.objects.create(
            report_type=Report.ReportType.SALES,
            store=store,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            created_by=admin_user,
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_create_report(self, api_client, admin_user, store, paid_order):
        target_date = paid_order.created_at.date()
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(self.LIST_URL, {
            'report_type': 'sales',
            'store_id': str(store.id),
            'date_from': str(target_date),
            'date_to': str(target_date),
            'format': 'json',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['report_type'] == 'sales'
        assert 'data' in response.data

    def test_create_report_invalid_dates_returns_400(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(self.LIST_URL, {
            'report_type': 'revenue',
            'date_from': '2026-01-31',
            'date_to': '2026-01-01',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_report_detail(self, api_client, admin_user, store):
        report = Report.objects.create(
            report_type=Report.ReportType.REVENUE,
            store=store,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(f'{self.LIST_URL}{report.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(report.id)

    def test_non_admin_cannot_create_report(self, api_client, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='regular_report', password='pass')
        api_client.force_authenticate(user=user)
        response = api_client.post(self.LIST_URL, {
            'report_type': 'sales',
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAnalyticsDashboardsAPI:
    URL = '/api/v1/admin/analytics/dashboards/'

    def test_create_dashboard(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(self.URL, {
            'name': 'Мой дашборд',
            'config': {'widgets': ['revenue_chart']},
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Мой дашборд'

    def test_list_returns_only_user_dashboards(self, api_client, admin_user, db):
        from django.contrib.auth import get_user_model
        from analytics.models import Dashboard
        User = get_user_model()
        other_user = User.objects.create_user(username='other_dash', password='pass', is_staff=True)

        Dashboard.objects.create(name='Mine', user=admin_user)
        Dashboard.objects.create(name='Other', user=other_user)

        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        names = [r['name'] for r in response.data['results']]
        assert 'Mine' in names
        assert 'Other' not in names
