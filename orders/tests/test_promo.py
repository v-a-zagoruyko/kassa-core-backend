"""Tests for PromoCode model and apply-promo API."""

import pytest
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from common.models import Address
from orders.models import Order, PromoCode
from stores.models import Store


@pytest.fixture
def address(db):
    return Address.objects.create(city='Тюмень', street='Ленина', house='1')


@pytest.fixture
def store(db, address):
    return Store.objects.create(name='Test Store', address=address)


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='promouser', password='pass123')


@pytest.fixture
def auth_client(db, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def valid_promo(db):
    now = timezone.now()
    return PromoCode.objects.create(
        code='TEST10',
        discount_type=PromoCode.DiscountType.PERCENT,
        discount_value=Decimal('10.00'),
        min_order_amount=Decimal('500.00'),
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
        max_uses=100,
        uses_count=0,
        order_types=PromoCode.OrderTypes.ALL,
    )


@pytest.fixture
def order_with_amount(db, store, user):
    order = Order.objects.create(
        store=store, customer=user, order_type='pickup',
        total_amount=Decimal('1000.00'),
        final_amount=Decimal('1000.00'),
    )
    return order


@pytest.mark.django_db
class TestPromoCodeModel:
    def test_valid_promo(self, valid_promo):
        ok, err = valid_promo.is_valid(Decimal('1000'), 'pickup')
        assert ok is True
        assert err == ''

    def test_expired_promo(self, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='EXPIRED',
            discount_type='fixed',
            discount_value=Decimal('100'),
            valid_from=now - timedelta(days=10),
            valid_until=now - timedelta(days=1),
            order_types='all',
        )
        ok, err = promo.is_valid(Decimal('500'), 'pickup')
        assert ok is False
        assert 'истёк' in err.lower()

    def test_limit_exhausted(self, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='MAXED',
            discount_type='fixed',
            discount_value=Decimal('50'),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            max_uses=5,
            uses_count=5,
            order_types='all',
        )
        ok, err = promo.is_valid(Decimal('500'), 'pickup')
        assert ok is False
        assert 'лимит' in err.lower()

    def test_min_amount_not_met(self, valid_promo):
        ok, err = valid_promo.is_valid(Decimal('100'), 'pickup')
        assert ok is False
        assert 'минимальная' in err.lower()

    def test_wrong_order_type(self, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='DELIVERY_ONLY',
            discount_type='fixed',
            discount_value=Decimal('100'),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            order_types='delivery',
        )
        ok, err = promo.is_valid(Decimal('500'), 'pickup')
        assert ok is False

    def test_calculate_percent_discount(self, valid_promo):
        discount = valid_promo.calculate_discount(Decimal('1000'))
        assert discount == Decimal('100.00')

    def test_calculate_fixed_discount(self, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='FIXED100',
            discount_type='fixed',
            discount_value=Decimal('100'),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            order_types='all',
        )
        discount = promo.calculate_discount(Decimal('500'))
        assert discount == Decimal('100')

    def test_discount_capped_at_order_amount(self, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='BIGDISCOUNT',
            discount_type='fixed',
            discount_value=Decimal('9999'),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            order_types='all',
        )
        discount = promo.calculate_discount(Decimal('100'))
        assert discount == Decimal('100')  # capped at order amount


@pytest.mark.django_db
class TestApplyPromoAPI:
    def test_apply_valid_promo(self, auth_client, order_with_amount, valid_promo):
        resp = auth_client.post(
            f'/api/v1/orders/{order_with_amount.id}/apply-promo/',
            {'code': 'TEST10'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['discount_amount'] == '100.00'
        assert resp.data['new_final_amount'] == '900.00'

        # Uses count incremented
        valid_promo.refresh_from_db()
        assert valid_promo.uses_count == 1

    def test_apply_invalid_code(self, auth_client, order_with_amount):
        resp = auth_client.post(
            f'/api/v1/orders/{order_with_amount.id}/apply-promo/',
            {'code': 'NOTEXIST'},
            format='json',
        )
        assert resp.status_code == 404

    def test_apply_expired_promo(self, auth_client, order_with_amount, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='EXP123',
            discount_type='fixed',
            discount_value=Decimal('100'),
            valid_from=now - timedelta(days=10),
            valid_until=now - timedelta(days=1),
            order_types='all',
        )
        resp = auth_client.post(
            f'/api/v1/orders/{order_with_amount.id}/apply-promo/',
            {'code': 'EXP123'},
            format='json',
        )
        assert resp.status_code == 400

    def test_apply_limit_exhausted_promo(self, auth_client, order_with_amount, db):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code='FULL123',
            discount_type='fixed',
            discount_value=Decimal('50'),
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            max_uses=3,
            uses_count=3,
            order_types='all',
        )
        resp = auth_client.post(
            f'/api/v1/orders/{order_with_amount.id}/apply-promo/',
            {'code': 'FULL123'},
            format='json',
        )
        assert resp.status_code == 400

    def test_apply_promo_missing_code(self, auth_client, order_with_amount):
        resp = auth_client.post(
            f'/api/v1/orders/{order_with_amount.id}/apply-promo/',
            {},
            format='json',
        )
        assert resp.status_code == 400
