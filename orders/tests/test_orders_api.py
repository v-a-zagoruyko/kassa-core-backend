"""Tests for Orders API endpoints."""

import pytest
from decimal import Decimal

from django.utils import timezone
from datetime import timedelta

from rest_framework.test import APIClient

from common.models import Address
from orders.models import Order, OrderItem, Reservation
from products.models import Category, Product, Stock
from stores.models import Store


@pytest.fixture
def address(db):
    return Address.objects.create(city='Тюмень', street='Ленина', house='1')


@pytest.fixture
def delivery_address(db):
    return Address.objects.create(city='Тюмень', street='Мира', house='5', apartment='10')


@pytest.fixture
def store(db, address):
    return Store.objects.create(name='Test Store', address=address)


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='apiuser', password='pass123')


@pytest.fixture
def other_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='otheruser', password='pass123')


@pytest.fixture
def auth_client(db, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def category(db):
    return Category.objects.create(name='Категория')


@pytest.fixture
def product(db, category):
    return Product.objects.create(name='Товар', category=category, price=Decimal('100.00'))


@pytest.fixture
def stock(db, product, store):
    return Stock.objects.create(product=product, store=store, quantity=Decimal('20.000'))


@pytest.mark.django_db
class TestOrderCreate:
    def test_create_pickup_order(self, auth_client, store):
        resp = auth_client.post('/api/v1/orders/', {
            'store_id': str(store.id),
            'order_type': 'pickup',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['order_type'] == 'pickup'
        assert resp.data['status'] == 'draft'

    def test_create_delivery_requires_address(self, auth_client, store):
        resp = auth_client.post('/api/v1/orders/', {
            'store_id': str(store.id),
            'order_type': 'delivery',
        }, format='json')
        assert resp.status_code == 400

    def test_create_delivery_with_address(self, auth_client, store, delivery_address):
        resp = auth_client.post('/api/v1/orders/', {
            'store_id': str(store.id),
            'order_type': 'delivery',
            'delivery_address_id': delivery_address.id,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['order_type'] == 'delivery'

    def test_unauthenticated_rejected(self, store):
        client = APIClient()
        resp = client.post('/api/v1/orders/', {'store_id': str(store.id), 'order_type': 'pickup'}, format='json')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestOrderList:
    def test_list_only_own_orders(self, auth_client, user, other_user, store):
        Order.objects.create(store=store, customer=user)
        Order.objects.create(store=store, customer=other_user)

        resp = auth_client.get('/api/v1/orders/')
        assert resp.status_code == 200
        assert resp.data['count'] == 1

    def test_list_paginated(self, auth_client, user, store):
        for _ in range(25):
            Order.objects.create(store=store, customer=user)

        resp = auth_client.get('/api/v1/orders/')
        assert resp.status_code == 200
        assert resp.data['count'] == 25
        assert len(resp.data['results']) == 20  # default page size


@pytest.mark.django_db
class TestOrderRetrieve:
    def test_retrieve_own_order(self, auth_client, user, store):
        order = Order.objects.create(store=store, customer=user)
        resp = auth_client.get(f'/api/v1/orders/{order.id}/')
        assert resp.status_code == 200
        assert str(resp.data['id']) == str(order.id)

    def test_cannot_retrieve_others_order(self, auth_client, other_user, store):
        order = Order.objects.create(store=store, customer=other_user)
        resp = auth_client.get(f'/api/v1/orders/{order.id}/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestOrderAddItem:
    def test_add_item(self, auth_client, user, store, product, stock):
        order = Order.objects.create(store=store, customer=user)
        resp = auth_client.post(f'/api/v1/orders/{order.id}/items/', {
            'product_id': str(product.id),
            'quantity': 2,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['quantity'] == 2

    def test_add_item_insufficient_stock(self, auth_client, user, store, product, stock):
        order = Order.objects.create(store=store, customer=user)
        resp = auth_client.post(f'/api/v1/orders/{order.id}/items/', {
            'product_id': str(product.id),
            'quantity': 999,
        }, format='json')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestOrderRemoveItem:
    def test_remove_item(self, auth_client, user, store, product, stock):
        order = Order.objects.create(store=store, customer=user)
        item = OrderItem.objects.create(
            order=order, product=product, quantity=1,
            price=product.price, subtotal=product.price,
        )
        resp = auth_client.delete(f'/api/v1/orders/{order.id}/items/{item.id}/')
        assert resp.status_code == 204
        assert order.items.count() == 0


@pytest.mark.django_db
class TestOrderSubmit:
    def test_submit_order(self, auth_client, user, store, product, stock, delivery_address):
        resp = auth_client.post('/api/v1/orders/', {
            'store_id': str(store.id),
            'order_type': 'delivery',
            'delivery_address_id': delivery_address.id,
        }, format='json')
        order_id = resp.data['id']

        auth_client.post(f'/api/v1/orders/{order_id}/items/', {
            'product_id': str(product.id),
            'quantity': 1,
        }, format='json')

        resp = auth_client.post(f'/api/v1/orders/{order_id}/submit/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'pending'

    def test_submit_empty_order_fails(self, auth_client, user, store):
        order = Order.objects.create(store=store, customer=user, order_type='pickup')
        resp = auth_client.post(f'/api/v1/orders/{order.id}/submit/')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestOrderCancel:
    def test_cancel_order(self, auth_client, user, store):
        order = Order.objects.create(store=store, customer=user, order_type='pickup')
        resp = auth_client.post(f'/api/v1/orders/{order.id}/cancel/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'cancelled'

    def test_cancel_completed_fails(self, auth_client, user, store):
        order = Order.objects.create(store=store, customer=user, status=Order.Status.COMPLETED)
        resp = auth_client.post(f'/api/v1/orders/{order.id}/cancel/')
        assert resp.status_code == 400
