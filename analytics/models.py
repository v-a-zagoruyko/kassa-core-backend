"""Модели аналитики: Report, Metric, Dashboard."""

from django.conf import settings
from django.db import models
from common.models import BaseModel


class Report(BaseModel):
    class ReportType(models.TextChoices):
        SALES = "sales", "Продажи"
        PRODUCTS = "products", "Товары"
        ORDERS = "orders", "Заказы"
        REVENUE = "revenue", "Выручка"

    class Format(models.TextChoices):
        JSON = "json", "JSON"
        EXCEL = "excel", "Excel"
        CSV = "csv", "CSV"
        PDF = "pdf", "PDF"

    report_type = models.CharField(max_length=20, choices=ReportType.choices, verbose_name="Тип отчёта")
    store = models.ForeignKey("stores.Store", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports", verbose_name="Точка продаж")
    date_from = models.DateField(verbose_name="Дата начала")
    date_to = models.DateField(verbose_name="Дата окончания")
    data = models.JSONField(default=dict, verbose_name="Данные")
    format = models.CharField(max_length=10, choices=Format.choices, default=Format.JSON, verbose_name="Формат")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports", verbose_name="Создал")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёты"

    def __str__(self):
        return f"{self.get_report_type_display()} {self.date_from} – {self.date_to}"


class Metric(BaseModel):
    class MetricType(models.TextChoices):
        REVENUE = "revenue", "Выручка"
        ORDERS_COUNT = "orders_count", "Количество заказов"
        AVG_ORDER_VALUE = "avg_order_value", "Средний чек"
        PRODUCTS_SOLD = "products_sold", "Продано товаров"

    metric_type = models.CharField(max_length=30, choices=MetricType.choices, verbose_name="Тип метрики")
    store = models.ForeignKey("stores.Store", on_delete=models.SET_NULL, null=True, blank=True, related_name="metrics", verbose_name="Точка продаж")
    date = models.DateField(verbose_name="Дата")
    value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Значение")
    metadata = models.JSONField(default=dict, verbose_name="Метаданные")

    class Meta:
        ordering = ["-date"]
        verbose_name = "Метрика"
        verbose_name_plural = "Метрики"
        constraints = [
            models.UniqueConstraint(fields=["metric_type", "store", "date"], condition=models.Q(store__isnull=False), name="unique_metric_store_date"),
            models.UniqueConstraint(fields=["metric_type", "date"], condition=models.Q(store__isnull=True), name="unique_metric_no_store_date"),
        ]

    def __str__(self):
        return f"{self.get_metric_type_display()} {self.date}: {self.value}"


class Dashboard(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Название")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboards", verbose_name="Пользователь")
    config = models.JSONField(default=dict, verbose_name="Конфигурация виджетов")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Дашборд"
        verbose_name_plural = "Дашборды"

    def __str__(self):
        return self.name
