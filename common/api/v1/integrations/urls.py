"""URL-маршруты для интеграционного API."""

from django.urls import path

from .views import ERPSyncView, WarehouseSyncView

urlpatterns = [
    path("admin/sync/warehouse/", WarehouseSyncView.as_view(), name="sync-warehouse"),
    path("admin/sync/erp/", ERPSyncView.as_view(), name="sync-erp"),
]
