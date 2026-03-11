"""Tests for Reservation model."""

import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from common.models import Address
from orders.models import Order, Reservation
from stores.models import Store
from products.models import Category, Product


@pytest.fixture
def store(db):
    address = Address.objects.create(city='Тюмень', street='Ленина', house='1')
    return Store.objects.create(name='Test Store', address=address)


@pytest.fixture
def product(db):
    cat = Category.objects.create(name='Категория')
    return Product.objects.create(name='Товар', category=cat, price=Decimal('100.00'))


@pytest.fixture
def order(db, store):
    return Order.objects.create(store=store)


@pytest.mark.django_db
class TestReservationModel:
    def test_create_reservation(self, order, product, store):
        expires_at = timezone.now() + timedelta(minutes=15)
        reservation = Reservation.objects.create(
            order=order,
            product=product,
            store=store,
            quantity=Decimal('2.000'),
            expires_at=expires_at,
        )
        assert reservation.status == Reservation.Status.ACTIVE
        assert reservation.released_at is None
        assert reservation.quantity == Decimal('2.000')

    def test_is_expired_false(self, order, product, store):
        expires_at = timezone.now() + timedelta(minutes=15)
        reservation = Reservation.objects.create(
            order=order,
            product=product,
            store=store,
            quantity=Decimal('1.000'),
            expires_at=expires_at,
        )
        assert reservation.is_expired() is False

    def test_is_expired_true(self, order, product, store):
        expires_at = timezone.now() - timedelta(minutes=1)
        reservation = Reservation.objects.create(
            order=order,
            product=product,
            store=store,
            quantity=Decimal('1.000'),
            expires_at=expires_at,
        )
        assert reservation.is_expired() is True

    def test_str(self, order, product, store):
        expires_at = timezone.now() + timedelta(minutes=15)
        reservation = Reservation.objects.create(
            order=order,
            product=product,
            store=store,
            quantity=Decimal('3.000'),
            expires_at=expires_at,
        )
        s = str(reservation)
        assert 'Резерв' in s
        assert 'Товар' in s

    def test_indexes_exist(self):
        index_names = [idx.fields for idx in Reservation._meta.indexes]
        assert ['product', 'store'] in index_names
        assert ['status', 'expires_at'] in index_names

    def test_status_choices(self):
        choices_values = [c[0] for c in Reservation.Status.choices]
        assert 'active' in choices_values
        assert 'completed' in choices_values
        assert 'expired' in choices_values
        assert 'released' in choices_values
