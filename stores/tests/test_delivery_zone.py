"""Tests for DeliveryZone model and DeliveryZoneService."""

import pytest
from decimal import Decimal

from django.test import TestCase

from common.models import Address
from stores.models import Store, DeliveryZone
from stores.services.delivery_zone_service import DeliveryZoneService, _euclidean_distance_km


@pytest.mark.django_db
class TestDeliveryZoneModel:
    def _make_store(self, lat=None, lon=None):
        address = Address.objects.create(city='Тюмень', street='Ленина', house='1')
        return Store.objects.create(
            name='Тест',
            address=address,
            lat=lat,
            lon=lon,
        )

    def _make_zone(self, store, name='Zone 1', radius_km='5.00', cost='200.00', time=30):
        return DeliveryZone.objects.create(
            store=store,
            name=name,
            radius_km=Decimal(radius_km) if radius_km else None,
            delivery_cost=Decimal(cost),
            delivery_time_minutes=time,
            min_order_amount=Decimal('500.00'),
        )

    def test_create_delivery_zone(self):
        store = self._make_store()
        zone = self._make_zone(store)
        assert zone.is_active is True
        assert zone.store == store
        assert zone.delivery_cost == Decimal('200.00')

    def test_zone_str(self):
        store = self._make_store()
        zone = self._make_zone(store, name='Ближняя зона')
        assert 'Ближняя зона' in str(zone)

    def test_inactive_zone_not_returned(self):
        store = self._make_store()
        zone = self._make_zone(store)
        zone.is_active = False
        zone.save()
        qs = DeliveryZoneService.get_zone_for_store(store.id)
        assert qs.count() == 0

    def test_get_zone_for_store(self):
        store = self._make_store()
        self._make_zone(store, name='Z1', radius_km='3.00')
        self._make_zone(store, name='Z2', radius_km='7.00')
        zones = DeliveryZoneService.get_zone_for_store(store.id)
        assert zones.count() == 2


@pytest.mark.django_db
class TestDeliveryZoneService:
    def _setup_store_with_zones(self, lat='57.1522', lon='65.5272'):
        address = Address.objects.create(city='Тюмень', street='Ленина', house='1')
        store = Store.objects.create(
            name='Тест магазин',
            address=address,
            lat=Decimal(lat),
            lon=Decimal(lon),
        )
        DeliveryZone.objects.create(
            store=store, name='Близко', radius_km=Decimal('3.00'),
            delivery_cost=Decimal('100.00'), delivery_time_minutes=20,
            min_order_amount=Decimal('300.00'),
        )
        DeliveryZone.objects.create(
            store=store, name='Далеко', radius_km=Decimal('10.00'),
            delivery_cost=Decimal('300.00'), delivery_time_minutes=60,
            min_order_amount=Decimal('500.00'),
        )
        return store

    def test_calculate_delivery_cost_near(self):
        store = self._setup_store_with_zones()
        cost = DeliveryZoneService.calculate_delivery_cost(store.id, Decimal('2.00'))
        assert cost == Decimal('100.00')

    def test_calculate_delivery_cost_far(self):
        store = self._setup_store_with_zones()
        cost = DeliveryZoneService.calculate_delivery_cost(store.id, Decimal('7.00'))
        assert cost == Decimal('300.00')

    def test_calculate_delivery_cost_out_of_range(self):
        store = self._setup_store_with_zones()
        cost = DeliveryZoneService.calculate_delivery_cost(store.id, Decimal('15.00'))
        assert cost == Decimal('0')

    def test_get_estimated_time(self):
        store = self._setup_store_with_zones()
        minutes = DeliveryZoneService.get_estimated_time(store.id, Decimal('2.00'))
        assert minutes == 20

    def test_check_delivery_available(self):
        store = self._setup_store_with_zones(lat='57.1522', lon='65.5272')
        # Same coordinates = distance 0
        result = DeliveryZoneService.check_delivery_availability(
            store.id, Decimal('57.1522'), Decimal('65.5272')
        )
        assert result['available'] is True
        assert result['delivery_cost'] == Decimal('100.00')

    def test_check_delivery_no_coords(self):
        address = Address.objects.create(city='Тюмень', street='Ленина', house='1')
        store = Store.objects.create(name='Без координат', address=address)
        result = DeliveryZoneService.check_delivery_availability(
            store.id, Decimal('57.1522'), Decimal('65.5272')
        )
        assert result['available'] is False

    def test_euclidean_distance(self):
        # Same point = 0 km
        d = _euclidean_distance_km(
            Decimal('57.0'), Decimal('65.0'),
            Decimal('57.0'), Decimal('65.0'),
        )
        assert d == Decimal('0')

    def test_euclidean_distance_nonzero(self):
        # ~1 degree lat = ~111 km
        d = _euclidean_distance_km(
            Decimal('57.0'), Decimal('65.0'),
            Decimal('58.0'), Decimal('65.0'),
        )
        assert abs(float(d) - 111.0) < 1.0
