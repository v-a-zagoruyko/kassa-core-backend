"""Django Admin для аналитики."""

from django.contrib import admin

from .models import Dashboard, Metric, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'store', 'date_from', 'date_to', 'format', 'created_by', 'created_at')
    list_filter = ('report_type', 'format', 'store')
    readonly_fields = ('created_at', 'updated_at', 'data')
    search_fields = ('report_type', 'store__name')
    date_hierarchy = 'created_at'


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ('metric_type', 'store', 'date', 'value')
    list_filter = ('metric_type', 'store', 'date')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('metric_type', 'store__name')
    date_hierarchy = 'date'


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('name', 'user__username')
