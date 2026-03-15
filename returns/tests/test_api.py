"""Тесты API возвратов."""

import pytest
from rest_framework import status

from returns.models import Return

RETURNS_URL = '/api/v1/admin/returns/'


@pytest.mark.django_db
class TestCreateReturn:
    def test_create_return_success(self, api_client, admin_user, completed_order):
        api_client.force_authenticate(user=admin_user)
        item = completed_order._test_item
        payload = {
            'order_id': str(completed_order.pk),
            'items': [
                {
                    'order_item_id': str(item.pk),
                    'quantity': 1,
                    'refund_amount': '100.00',
                }
            ],
            'refund_method': 'cash',
        }
        response = api_client.post(RETURNS_URL, data=payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Return.objects.filter(order=completed_order).exists()

    def test_create_return_order_older_than_12h_returns_400(self, api_client, admin_user, completed_order):
        from django.utils import timezone
        completed_order.created_at = timezone.now() - timezone.timedelta(hours=13)
        completed_order.save()

        api_client.force_authenticate(user=admin_user)
        item = completed_order._test_item
        payload = {
            'order_id': str(completed_order.pk),
            'items': [
                {
                    'order_item_id': str(item.pk),
                    'quantity': 1,
                    'refund_amount': '100.00',
                }
            ],
            'refund_method': 'cash',
        }
        response = api_client.post(RETURNS_URL, data=payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_return_requires_auth(self, api_client, completed_order):
        payload = {
            'order_id': str(completed_order.pk),
            'items': [],
            'refund_method': 'cash',
        }
        response = api_client.post(RETURNS_URL, data=payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_return_regular_user_forbidden(self, api_client, regular_user, completed_order):
        api_client.force_authenticate(user=regular_user)
        item = completed_order._test_item
        payload = {
            'order_id': str(completed_order.pk),
            'items': [
                {
                    'order_item_id': str(item.pk),
                    'quantity': 1,
                    'refund_amount': '100.00',
                }
            ],
            'refund_method': 'cash',
        }
        response = api_client.post(RETURNS_URL, data=payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestListReturns:
    def test_list_requires_auth(self, api_client):
        response = api_client.get(RETURNS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_as_admin(self, api_client, admin_user, completed_order):
        api_client.force_authenticate(user=admin_user)
        item = completed_order._test_item
        from returns.services import ReturnService
        ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        response = api_client.get(RETURNS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_filter_by_order_id(self, api_client, admin_user, completed_order):
        api_client.force_authenticate(user=admin_user)
        item = completed_order._test_item
        from returns.services import ReturnService
        ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        response = api_client.get(RETURNS_URL, {'order_id': str(completed_order.pk)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestReturnDetail:
    def test_detail_as_admin(self, api_client, admin_user, completed_order):
        api_client.force_authenticate(user=admin_user)
        item = completed_order._test_item
        from returns.services import ReturnService
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        response = api_client.get(f'{RETURNS_URL}{ret.pk}/')
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(ret.pk)


@pytest.mark.django_db
class TestProcessRefundAPI:
    def test_process_cash_refund(self, api_client, admin_user, completed_order):
        api_client.force_authenticate(user=admin_user)
        item = completed_order._test_item
        from returns.services import ReturnService
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        response = api_client.post(f'{RETURNS_URL}{ret.pk}/process/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == Return.Status.COMPLETED

    def test_process_requires_auth(self, api_client, admin_user, completed_order):
        item = completed_order._test_item
        from returns.services import ReturnService
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        response = api_client.post(f'{RETURNS_URL}{ret.pk}/process/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_process_regular_user_forbidden(self, api_client, regular_user, admin_user, completed_order):
        item = completed_order._test_item
        from returns.services import ReturnService
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        api_client.force_authenticate(user=regular_user)
        response = api_client.post(f'{RETURNS_URL}{ret.pk}/process/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
