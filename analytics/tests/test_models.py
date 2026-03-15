"""Тесты моделей аналитики."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from analytics.models import Dashboard, Metric, Report


@pytest.mark.django_db
class TestReportModel:
    def test_create_report(self, store, admin_user):
        report = Report.objects.create(
            report_type=Report.ReportType.SALES,
            store=store,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            created_by=admin_user,
        )
        assert report.pk is not None
        assert report.format == Report.Format.JSON
        assert report.data == {}
        assert str(report.date_from) in str(report)

    def test_report_without_store(self, admin_user):
        report = Report.objects.create(
            report_type=Report.ReportType.REVENUE,
            store=None,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
        assert report.store is None

    def test_report_soft_delete(self, store):
        report = Report.objects.create(
            report_type=Report.ReportType.ORDERS,
            store=store,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )
        pk = report.pk
        report.delete()
        assert not Report.objects.filter(pk=pk).exists()
        assert Report.all_objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestMetricModel:
    def test_create_metric(self, store):
        metric = Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE,
            store=store,
            date=date(2026, 1, 15),
            value=Decimal('5000.00'),
        )
        assert metric.pk is not None
        assert metric.metadata == {}
        assert 'Выручка' in str(metric)

    def test_unique_constraint_with_store(self, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE,
            store=store,
            date=date(2026, 2, 1),
            value=Decimal('1000.00'),
        )
        with pytest.raises(IntegrityError):
            Metric.objects.create(
                metric_type=Metric.MetricType.REVENUE,
                store=store,
                date=date(2026, 2, 1),
                value=Decimal('2000.00'),
            )

    def test_unique_constraint_without_store(self):
        Metric.objects.create(
            metric_type=Metric.MetricType.ORDERS_COUNT,
            store=None,
            date=date(2026, 2, 2),
            value=Decimal('10.00'),
        )
        with pytest.raises(IntegrityError):
            Metric.objects.create(
                metric_type=Metric.MetricType.ORDERS_COUNT,
                store=None,
                date=date(2026, 2, 2),
                value=Decimal('20.00'),
            )

    def test_same_metric_different_dates_allowed(self, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE,
            store=store,
            date=date(2026, 3, 1),
            value=Decimal('100.00'),
        )
        m2 = Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE,
            store=store,
            date=date(2026, 3, 2),
            value=Decimal('200.00'),
        )
        assert m2.pk is not None


@pytest.mark.django_db
class TestDashboardModel:
    def test_create_dashboard(self, admin_user):
        dashboard = Dashboard.objects.create(
            name='Мой дашборд',
            user=admin_user,
            config={'widgets': []},
        )
        assert dashboard.pk is not None
        assert dashboard.is_active is True
        assert str(dashboard) == 'Мой дашборд'

    def test_dashboard_cascade_delete_with_user(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='tmp_dash_user', password='pass')
        dashboard = Dashboard.objects.create(name='Tmp', user=user)
        pk = dashboard.pk
        user.hard_delete()
        assert not Dashboard.objects.filter(pk=pk).exists()
