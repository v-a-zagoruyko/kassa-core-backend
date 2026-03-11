"""Tests for order status tracking: signal and API."""

import pytest
from decimal import Decimal

from rest_framework.test import APIClient

from common.models import Address
from orders.models import Order, OrderStatusLog
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
    return User.objects.create_user(username='trackuser', password='pass123')


@pytest.fixture
def auth_client(db, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.mark.django_db
class TestOrderStatusLogSignal:
    def test_signal_creates_log_on_creation(self, store):
        order = Order.objects.create(store=store)
        logs = OrderStatusLog.objects.filter(order=order)
        assert logs.count() == 1
        assert logs.first().status == Order.Status.DRAFT

    def test_signal_creates_log_on_status_change(self, store):
        order = Order.objects.create(store=store)
        initial_count = OrderStatusLog.objects.filter(order=order).count()

        order.status = Order.Status.PENDING
        order.save()

        logs = OrderStatusLog.objects.filter(order=order).order_by('created_at')
        assert logs.count() == initial_count + 1
        assert logs.last().status == Order.Status.PENDING

    def test_signal_no_log_when_status_unchanged(self, store):
        order = Order.objects.create(store=store)
        initial_count = OrderStatusLog.objects.filter(order=order).count()

        order.courier_comment = 'Updated comment'
        order.save()

        assert OrderStatusLog.objects.filter(order=order).count() == initial_count

    def test_status_log_ordering(self, store):
        order = Order.objects.create(store=store)
        order.status = Order.Status.PENDING
        order.save()
        order.status = Order.Status.CANCELLED
        order.save()

        logs = OrderStatusLog.objects.filter(order=order).order_by('created_at')
        statuses = [log.status for log in logs]
        assert statuses[0] == Order.Status.DRAFT
        assert statuses[1] == Order.Status.PENDING
        assert statuses[2] == Order.Status.CANCELLED


@pytest.mark.django_db
class TestOrderTrackingAPI:
    def test_tracking_endpoint(self, auth_client, user, store):
        order = Order.objects.create(store=store, customer=user)
        resp = auth_client.get(f'/api/v1/orders/{order.id}/tracking/')
        assert resp.status_code == 200
        data = resp.data
        assert data['current_status'] == 'draft'
        assert 'history' in data
        assert len(data['history']) >= 1
        assert data['history'][0]['status'] == 'draft'

    def test_tracking_status_changes_in_history(self, auth_client, user, store):
        order = Order.objects.create(store=store, customer=user)
        order.status = Order.Status.PENDING
        order.save()

        resp = auth_client.get(f'/api/v1/orders/{order.id}/tracking/')
        assert resp.status_code == 200
        history = resp.data['history']
        statuses = [h['status'] for h in history]
        assert Order.Status.DRAFT in statuses
        assert Order.Status.PENDING in statuses

    def test_tracking_other_user_order_404(self, auth_client, store):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(username='other2', password='pass')
        order = Order.objects.create(store=store, customer=other)
        resp = auth_client.get(f'/api/v1/orders/{order.id}/tracking/')
        assert resp.status_code == 404
