"""Views для синхронизации складских и ERP-интеграций."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api.v1.fiscal.permissions import IsAdminOrManager
from integrations.erp import ERPService
from integrations.warehouse import WarehouseService


class WarehouseSyncView(APIView):
    """POST /api/v1/admin/sync/warehouse/ — запуск синхронизации остатков."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request):
        store_id = request.data.get("store_id")
        result = WarehouseService().sync_inventory(store_id=store_id)
        return Response({"status": "ok", "synced": result["synced"]})


class ERPSyncView(APIView):
    """POST /api/v1/admin/sync/erp/ — запуск синхронизации номенклатуры ERP."""

    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def post(self, request):
        ERPService().sync_products()
        return Response({"status": "ok"})
