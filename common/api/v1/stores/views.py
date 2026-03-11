import logging
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stores.models import DeliveryZone, Store
from stores.services.delivery_zone_service import DeliveryZoneService
from .serializers import DeliveryZoneSerializer, DeliveryCheckSerializer

logger = logging.getLogger(__name__)


class StoreDeliveryZonesView(APIView):
    """
    GET /api/v1/stores/{id}/delivery-zones/

    List active delivery zones for a store.
    """

    def get(self, request, store_id):
        store = get_object_or_404(Store, pk=store_id)
        zones = DeliveryZone.objects.filter(store=store, is_active=True).order_by('radius_km')
        serializer = DeliveryZoneSerializer(zones, many=True)
        return Response(serializer.data)


class DeliveryCheckView(APIView):
    """
    POST /api/v1/delivery/check/

    Check delivery availability for a location.

    Body: {store_id, lat, lon}
    Response: {available, delivery_cost, estimated_minutes, min_order_amount}
    """

    def post(self, request):
        serializer = DeliveryCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        result = DeliveryZoneService.check_delivery_availability(
            store_id=data['store_id'],
            client_lat=Decimal(str(data['lat'])),
            client_lon=Decimal(str(data['lon'])),
        )
        # Remove internal field
        result.pop('distance_km', None)
        return Response(result)
