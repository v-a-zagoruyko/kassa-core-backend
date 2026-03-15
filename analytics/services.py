"""AnalyticsService."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import DecimalField, QuerySet, Sum
from django.db.models.functions import Coalesce

from orders.models import Order, OrderItem

from .models import Dashboard, Metric, Report


class AnalyticsService:

    @classmethod
    def calculate_daily_metrics(cls, store_id, target_date: date) -> list[Metric]:
        paid_orders = Order.objects.filter(
            store_id=store_id,
            status=Order.Status.PAID,
            created_at__date=target_date,
        )
        orders_count = paid_orders.count()
        total_revenue = paid_orders.aggregate(
            total=Coalesce(Sum("final_amount"), Decimal("0"), output_field=DecimalField())
        )["total"] or Decimal("0")
        avg_order_value = (
            (total_revenue / orders_count).quantize(Decimal("0.01"))
            if orders_count > 0 else Decimal("0")
        )
        products_sold = OrderItem.objects.filter(order__in=paid_orders).aggregate(
            total=Coalesce(Sum("quantity"), 0)
        )["total"] or 0

        results = []
        for metric_type, value in [
            (Metric.MetricType.REVENUE, total_revenue),
            (Metric.MetricType.ORDERS_COUNT, Decimal(str(orders_count))),
            (Metric.MetricType.AVG_ORDER_VALUE, avg_order_value),
            (Metric.MetricType.PRODUCTS_SOLD, Decimal(str(products_sold))),
        ]:
            metric, _ = Metric.objects.update_or_create(
                metric_type=metric_type,
                store_id=store_id,
                date=target_date,
                defaults={"value": value},
            )
            results.append(metric)
        return results

    @classmethod
    def get_metrics(cls, store_id, date_from, date_to, metric_types: Optional[list] = None) -> QuerySet:
        qs = Metric.objects.filter(date__gte=date_from, date__lte=date_to)
        if store_id is not None:
            qs = qs.filter(store_id=store_id)
        if metric_types:
            qs = qs.filter(metric_type__in=metric_types)
        return qs

    @classmethod
    def generate_report(cls, report_type: str, store_id=None, date_from: date = None,
                        date_to: date = None, format: str = Report.Format.JSON, user_id=None) -> Report:
        if format != Report.Format.JSON:
            data = {"message": "export not implemented yet"}
        else:
            paid_orders = Order.objects.filter(status=Order.Status.PAID,
                                                created_at__date__gte=date_from,
                                                created_at__date__lte=date_to)
            if store_id:
                paid_orders = paid_orders.filter(store_id=store_id)
            orders_count = paid_orders.count()
            total_revenue = paid_orders.aggregate(
                total=Coalesce(Sum("final_amount"), Decimal("0"), output_field=DecimalField())
            )["total"] or Decimal("0")
            products_sold = OrderItem.objects.filter(order__in=paid_orders).aggregate(
                total=Coalesce(Sum("quantity"), 0)
            )["total"] or 0
            data = {
                "total_revenue": str(total_revenue.quantize(Decimal("0.01"))),
                "total_orders": orders_count,
                "avg_order_value": str((total_revenue / orders_count).quantize(Decimal("0.01")) if orders_count > 0 else Decimal("0")),
                "products_sold": products_sold,
            }
        return Report.objects.create(
            report_type=report_type, store_id=store_id,
            date_from=date_from, date_to=date_to,
            data=data, format=format, created_by_id=user_id,
        )

    @classmethod
    def get_user_dashboards(cls, user_id) -> QuerySet:
        return Dashboard.objects.filter(user_id=user_id, is_active=True)
