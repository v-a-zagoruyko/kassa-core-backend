"""DeliveryZoneService — business logic for delivery zones."""

import math
import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# 1 degree of latitude/longitude ≈ 111 km
KM_PER_DEGREE = Decimal("111")


def _euclidean_distance_km(
    store_lat: Decimal,
    store_lon: Decimal,
    client_lat: Decimal,
    client_lon: Decimal,
) -> Decimal:
    """Calculate Euclidean distance in km between two lat/lon points."""
    dlat = (client_lat - store_lat) * KM_PER_DEGREE
    dlon = (client_lon - store_lon) * KM_PER_DEGREE
    return Decimal(str(math.sqrt(float(dlat ** 2 + dlon ** 2))))


class DeliveryZoneService:
    @staticmethod
    def get_zone_for_store(store_id):
        """Return all active DeliveryZone objects for a store.

        Args:
            store_id: UUID or int of the store.

        Returns:
            QuerySet[DeliveryZone] — active zones ordered by radius_km.
        """
        from stores.models import DeliveryZone

        return DeliveryZone.objects.filter(store_id=store_id, is_active=True)

    @staticmethod
    def get_nearest_zone(store_id, distance_km: Decimal):
        """Find the nearest active zone that covers the given distance.

        Returns the zone with the smallest radius_km that is >= distance_km.
        If radius_km is None — the zone covers any distance.

        Args:
            store_id: UUID or int of the store.
            distance_km: distance from store to client in km.

        Returns:
            DeliveryZone instance or None.
        """
        from stores.models import DeliveryZone

        zones = (
            DeliveryZone.objects.filter(store_id=store_id, is_active=True)
            .order_by("radius_km")
        )
        for zone in zones:
            if zone.radius_km is None or zone.radius_km >= distance_km:
                return zone
        return None

    @staticmethod
    def calculate_delivery_cost(store_id, distance_km: Decimal) -> Decimal:
        """Return delivery cost for given store/distance.

        Args:
            store_id: UUID or int of the store.
            distance_km: distance from store to client in km.

        Returns:
            Decimal delivery cost; Decimal('0') if no zone covers the distance.
        """
        zone = DeliveryZoneService.get_nearest_zone(store_id, distance_km)
        if zone is None:
            return Decimal("0")
        return zone.delivery_cost

    @staticmethod
    def get_estimated_time(store_id, distance_km: Decimal) -> int:
        """Return estimated delivery time in minutes.

        Args:
            store_id: UUID or int of the store.
            distance_km: distance from store to client in km.

        Returns:
            int minutes; 0 if no zone covers the distance.
        """
        zone = DeliveryZoneService.get_nearest_zone(store_id, distance_km)
        if zone is None:
            return 0
        return zone.delivery_time_minutes

    @staticmethod
    def check_delivery_availability(
        store_id,
        client_lat: Decimal,
        client_lon: Decimal,
    ) -> dict:
        """Check if delivery is available to a given location.

        Uses simple Euclidean distance (1 degree ≈ 111 km).

        Args:
            store_id: UUID or int of the store.
            client_lat: client latitude.
            client_lon: client longitude.

        Returns:
            dict with keys: available, delivery_cost, estimated_minutes,
            min_order_amount, distance_km.
        """
        from stores.models import Store

        try:
            store = Store.objects.get(pk=store_id)
        except Store.DoesNotExist:
            return {
                "available": False,
                "delivery_cost": Decimal("0"),
                "estimated_minutes": 0,
                "min_order_amount": Decimal("0"),
                "distance_km": None,
            }

        if store.lat is None or store.lon is None:
            logger.warning("Store %s has no coordinates set", store_id)
            return {
                "available": False,
                "delivery_cost": Decimal("0"),
                "estimated_minutes": 0,
                "min_order_amount": Decimal("0"),
                "distance_km": None,
            }

        distance_km = _euclidean_distance_km(
            Decimal(str(store.lat)),
            Decimal(str(store.lon)),
            Decimal(str(client_lat)),
            Decimal(str(client_lon)),
        )

        zone = DeliveryZoneService.get_nearest_zone(store_id, distance_km)
        if zone is None:
            return {
                "available": False,
                "delivery_cost": Decimal("0"),
                "estimated_minutes": 0,
                "min_order_amount": Decimal("0"),
                "distance_km": distance_km,
            }

        return {
            "available": True,
            "delivery_cost": zone.delivery_cost,
            "estimated_minutes": zone.delivery_time_minutes,
            "min_order_amount": zone.min_order_amount,
            "distance_km": distance_km,
        }
