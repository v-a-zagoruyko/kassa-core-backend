"""Тесты AnalyticsService."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from analytics.models import Metric, Report
from analytics.services import AnalyticsService


@pytest.mark.django_db
class TestCalculateDailyMetrics:
    def test_calculates_metrics_from_paid_orders(self, paid_order, store):
        target_date = paid_order.created_at.date()
        metrics = AnalyticsService.calculate_daily_metrics(store.id, target_date)

        assert len(metrics) == 4
        by_type = {m.metric_type: m for m in metrics}

        assert by_type[Metric.MetricType.REVENUE].value == Decimal('300.00')
        assert by_type[Metric.MetricType.ORDERS_COUNT].value == Decimal('1')
        assert by_type[Metric.MetricType.AVG_ORDER_VALUE].value == Decimal('300.00')
        assert by_type[Metric.MetricType.PRODUCTS_SOLD].value == Decimal('2')

    def test_upsert_updates_existing_metric(self, paid_order, store):
        target_date = paid_order.created_at.date()
        AnalyticsService.calculate_daily_metrics(store.id, target_date)
        AnalyticsService.calculate_daily_metrics(store.id, target_date)

        count = Metric.objects.filter(store=store, date=target_date).count()
        assert count == 4  # no duplicates

    def test_returns_zero_metrics_for_empty_day(self, store):
        future_date = date.today() + timedelta(days=365)
        metrics = AnalyticsService.calculate_daily_metrics(store.id, future_date)
        by_type = {m.metric_type: m for m in metrics}
        assert by_type[Metric.MetricType.REVENUE].value == Decimal('0')
        assert by_type[Metric.MetricType.ORDERS_COUNT].value == Decimal('0')

    def test_cancelled_orders_not_counted(self, store, db):
        from django.contrib.auth import get_user_model
        from products.models import Category, Product
        from orders.models import Order, OrderItem

        User = get_user_model()
        user = User.objects.create_user(username='cust_cancelled', password='pass')
        category = Category.objects.create(name='CatX', slug='catx-svc')
        product = Product.objects.create(
            name='ProdX', slug='prodx-svc', category=category, price=Decimal('100.00'),
        )
        order = Order.objects.create(
            store=store,
            customer=user,
            status=Order.Status.CANCELLED,
            total_amount=Decimal('100.00'),
            final_amount=Decimal('100.00'),
            payment_method=Order.PaymentMethod.CASH,
        )
        OrderItem.objects.create(
            order=order, product=product, quantity=1,
            price=Decimal('100.00'), subtotal=Decimal('100.00'),
        )
        target_date = order.created_at.date()
        metrics = AnalyticsService.calculate_daily_metrics(store.id, target_date)
        by_type = {m.metric_type: m for m in metrics}
        assert by_type[Metric.MetricType.REVENUE].value == Decimal('0')


@pytest.mark.django_db
class TestGetMetrics:
    def test_filters_by_store_and_date_range(self, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE, store=store,
            date=date(2026, 1, 10), value=Decimal('100'),
        )
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE, store=store,
            date=date(2026, 1, 20), value=Decimal('200'),
        )
        qs = AnalyticsService.get_metrics(store.id, date(2026, 1, 15), date(2026, 1, 25))
        assert qs.count() == 1
        assert qs.first().value == Decimal('200')

    def test_filters_by_metric_types(self, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE, store=store,
            date=date(2026, 2, 5), value=Decimal('500'),
        )
        Metric.objects.create(
            metric_type=Metric.MetricType.ORDERS_COUNT, store=store,
            date=date(2026, 2, 5), value=Decimal('10'),
        )
        qs = AnalyticsService.get_metrics(
            store.id, date(2026, 2, 1), date(2026, 2, 28),
            metric_types=[Metric.MetricType.REVENUE],
        )
        assert qs.count() == 1
        assert qs.first().metric_type == Metric.MetricType.REVENUE

    def test_none_store_returns_all_stores(self, store):
        Metric.objects.create(
            metric_type=Metric.MetricType.REVENUE, store=store,
            date=date(2026, 3, 1), value=Decimal('100'),
        )
        qs = AnalyticsService.get_metrics(None, date(2026, 3, 1), date(2026, 3, 31))
        assert qs.count() == 1


@pytest.mark.django_db
class TestGenerateReport:
    def test_generate_sales_report(self, paid_order, store):
        target_date = paid_order.created_at.date()
        report = AnalyticsService.generate_report(
            report_type=Report.ReportType.SALES,
            store_id=store.id,
            date_from=target_date,
            date_to=target_date,
        )
        assert report.pk is not None
        assert report.report_type == Report.ReportType.SALES
        assert 'total_revenue' in report.data
        assert report.data['total_orders'] == 1

    def test_generate_revenue_report(self, paid_order, store):
        target_date = paid_order.created_at.date()
        report = AnalyticsService.generate_report(
            report_type=Report.ReportType.REVENUE,
            store_id=store.id,
            date_from=target_date,
            date_to=target_date,
        )
        assert report.data['total_revenue'] == '300.00'

    def test_non_json_format_returns_stub(self, store):
        report = AnalyticsService.generate_report(
            report_type=Report.ReportType.ORDERS,
            store_id=store.id,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            format=Report.Format.EXCEL,
        )
        assert report.data == {'message': 'export not implemented yet'}

    def test_report_saved_with_user(self, store, admin_user):
        report = AnalyticsService.generate_report(
            report_type=Report.ReportType.ORDERS,
            store_id=store.id,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            user_id=admin_user.id,
        )
        assert report.created_by_id == admin_user.id
