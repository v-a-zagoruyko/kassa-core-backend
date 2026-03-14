"""Тесты сервисного слоя фискального домена."""

import pytest

from fiscal.models import Receipt
from fiscal.services import ReceiptService


@pytest.mark.django_db
class TestGenerateReceipt:
    def test_generate_receipt_success(self, paid_order):
        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)

        assert receipt.pk is not None
        assert receipt.order == paid_order
        assert receipt.status == Receipt.Status.PENDING
        assert receipt.receipt_number.startswith('RCP-')
        assert receipt.items.count() == 1

    def test_receipt_number_format(self, paid_order):
        from django.utils import timezone

        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)
        date_str = timezone.now().strftime('%Y%m%d')
        assert receipt.receipt_number == f'RCP-{date_str}-000001'

    def test_fiscal_data_structure(self, paid_order):
        receipt = ReceiptService.generate_receipt(order_id=paid_order.pk)

        assert receipt.fiscal_data['type'] == 'income'
        assert 'total' in receipt.fiscal_data
        assert 'items' in receipt.fiscal_data
        assert len(receipt.fiscal_data['items']) == 1

    def test_raises_if_order_not_paid(self, db):
        from django.contrib.auth import get_user_model
        from common.models import Address
        from orders.models import Order
        from stores.models import Store

        User = get_user_model()
        user = User.objects.create_user(username='u2', password='p')
        address = Address.objects.create(city='Г', street='У', house='1')
        store = Store.objects.create(name='S2', address=address)
        order = Order.objects.create(
            store=store,
            customer=user,
            status=Order.Status.PENDING,
            total_amount='0',
            final_amount='0',
        )

        with pytest.raises(ValueError, match='paid'):
            ReceiptService.generate_receipt(order_id=order.pk)

    def test_raises_if_receipt_already_exists(self, paid_order):
        ReceiptService.generate_receipt(order_id=paid_order.pk)

        with pytest.raises(ValueError, match='уже существует'):
            ReceiptService.generate_receipt(order_id=paid_order.pk)


@pytest.mark.django_db
class TestHandleOFDResponse:
    def _create_receipt(self, paid_order):
        return Receipt.objects.create(
            order=paid_order,
            receipt_number='RCP-20260314-000001',
            fiscal_data={},
            status=Receipt.Status.SENT,
        )

    def test_confirmed_status(self, paid_order):
        receipt = self._create_receipt(paid_order)
        ReceiptService.handle_ofd_response(
            receipt_id=receipt.pk,
            response={'status': 'confirmed', 'response_data': {}, 'error_message': '', 'status_code': 200},
        )
        receipt.refresh_from_db()
        assert receipt.status == Receipt.Status.CONFIRMED
        assert receipt.confirmed_at is not None

    def test_failed_status(self, paid_order):
        receipt = self._create_receipt(paid_order)
        ReceiptService.handle_ofd_response(
            receipt_id=receipt.pk,
            response={'status': 'failed', 'response_data': {}, 'error_message': 'Ошибка', 'status_code': 500},
        )
        receipt.refresh_from_db()
        assert receipt.status == Receipt.Status.FAILED
        assert receipt.error_message == 'Ошибка'

    def test_ofd_response_record_created(self, paid_order):
        from fiscal.models import OFDResponse

        receipt = self._create_receipt(paid_order)
        ReceiptService.handle_ofd_response(
            receipt_id=receipt.pk,
            response={'status': 'confirmed', 'response_data': {'key': 'val'}, 'error_message': '', 'status_code': 200},
        )
        assert OFDResponse.objects.filter(receipt=receipt).count() == 1
