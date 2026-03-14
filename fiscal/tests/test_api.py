"""Тесты API фискального домена."""

import pytest
from rest_framework import status

from fiscal.models import Receipt


WEBHOOK_URL = '/api/v1/integrations/ofd/webhook/'


@pytest.mark.django_db
class TestOFDWebhook:
    def _make_sent_receipt(self, paid_order):
        return Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
            status=Receipt.Status.SENT,
        )

    def test_webhook_success(self, api_client, paid_order):
        receipt = self._make_sent_receipt(paid_order)
        payload = {
            'receipt_id': str(receipt.pk),
            'status': 'confirmed',
            'response_data': {},
            'error_message': '',
        }
        response = api_client.post(WEBHOOK_URL, data=payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'status': 'ok'}
        receipt.refresh_from_db()
        assert receipt.status == Receipt.Status.CONFIRMED

    def test_webhook_invalid_token(self, api_client, paid_order, settings):
        settings.OFD_WEBHOOK_TOKEN = 'secret-token'
        receipt = self._make_sent_receipt(paid_order)
        payload = {
            'receipt_id': str(receipt.pk),
            'status': 'confirmed',
        }
        response = api_client.post(
            WEBHOOK_URL,
            data=payload,
            format='json',
            HTTP_X_OFD_TOKEN='wrong-token',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_webhook_correct_token(self, api_client, paid_order, settings):
        settings.OFD_WEBHOOK_TOKEN = 'secret-token'
        receipt = self._make_sent_receipt(paid_order)
        payload = {
            'receipt_id': str(receipt.pk),
            'status': 'confirmed',
            'response_data': {},
            'error_message': '',
        }
        response = api_client.post(
            WEBHOOK_URL,
            data=payload,
            format='json',
            HTTP_X_OFD_TOKEN='secret-token',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_webhook_invalid_body(self, api_client):
        response = api_client.post(WEBHOOK_URL, data={'bad': 'data'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_webhook_invalid_status_choice(self, api_client, paid_order):
        receipt = self._make_sent_receipt(paid_order)
        payload = {
            'receipt_id': str(receipt.pk),
            'status': 'unknown_status',
        }
        response = api_client.post(WEBHOOK_URL, data=payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAdminReceiptAPI:
    RECEIPTS_URL = '/api/v1/admin/fiscal/receipts/'

    def _make_receipt(self, paid_order):
        return Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={'type': 'income'},
            status=Receipt.Status.PENDING,
        )

    def test_list_receipts_requires_auth(self, api_client):
        response = api_client.get(self.RECEIPTS_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_receipts_as_admin(self, api_client, admin_user, paid_order):
        self._make_receipt(paid_order)
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(self.RECEIPTS_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_detail_receipt(self, api_client, admin_user, paid_order):
        receipt = self._make_receipt(paid_order)
        api_client.force_authenticate(user=admin_user)
        response = api_client.get(f'{self.RECEIPTS_URL}{receipt.pk}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['receipt_number'] == receipt.receipt_number

    def test_generate_receipt(self, api_client, admin_user, paid_order):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f'{self.RECEIPTS_URL}{paid_order.pk}/generate/')
        assert response.status_code == status.HTTP_201_CREATED
        assert Receipt.objects.filter(order=paid_order).exists()

    def test_generate_receipt_twice_returns_400(self, api_client, admin_user, paid_order):
        api_client.force_authenticate(user=admin_user)
        api_client.post(f'{self.RECEIPTS_URL}{paid_order.pk}/generate/')
        response = api_client.post(f'{self.RECEIPTS_URL}{paid_order.pk}/generate/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
