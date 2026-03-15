"""Тесты моделей и сервиса возвратов."""

from decimal import Decimal

import pytest

from returns.models import Return, ReturnItem, ReturnReason, ReturnStatus
from returns.services import ReturnService


@pytest.mark.django_db
class TestReturnCreation:
    def test_create_return_basic(self, completed_order, admin_user):
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        assert ret.pk is not None
        assert ret.status == Return.Status.PENDING
        assert ret.total_amount == Decimal('100.00')
        assert ret.items.count() == 1

    def test_create_return_creates_status_history(self, completed_order, admin_user):
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CARD,
        )
        assert ReturnStatus.objects.filter(return_obj=ret).count() == 1

    def test_create_return_with_reason(self, completed_order, admin_user):
        reason = ReturnReason.objects.create(code='DEFECT', name='Брак')
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '50.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
            reason_id=reason.pk,
            comment='Товар бракованный',
        )
        assert ret.reason_id == reason.pk
        assert ret.comment == 'Товар бракованный'


@pytest.mark.django_db
class TestReturnServiceValidation:
    def test_reject_non_paid_order(self, db):
        from django.contrib.auth import get_user_model
        from common.models import Address
        from stores.models import Store
        from orders.models import Order

        User = get_user_model()
        user = User.objects.create_user(username='u_rej', password='pass')
        address = Address.objects.create(city='C', street='S', house='1')
        store = Store.objects.create(name='S', address=address)
        order = Order.objects.create(
            store=store,
            status=Order.Status.PENDING,
            total_amount='100.00',
            final_amount='100.00',
        )
        with pytest.raises(ValueError, match='Возврат возможен'):
            ReturnService.create_return(
                order_id=order.pk,
                items=[{'order_item_id': order.pk, 'quantity': 1, 'refund_amount': '10.00'}],
                processed_by_user_id=user.pk,
                refund_method=Return.RefundMethod.CASH,
            )

    def test_reject_order_older_than_12h(self, completed_order, admin_user):
        from django.utils import timezone
        completed_order.created_at = timezone.now() - timezone.timedelta(hours=13)
        completed_order.save()

        item = completed_order._test_item
        with pytest.raises(ValueError, match='12 часов'):
            ReturnService.create_return(
                order_id=completed_order.pk,
                items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
                processed_by_user_id=admin_user.pk,
                refund_method=Return.RefundMethod.CASH,
            )

    def test_reject_duplicate_active_return(self, completed_order, admin_user):
        item = completed_order._test_item
        ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        with pytest.raises(ValueError, match='активный возврат'):
            ReturnService.create_return(
                order_id=completed_order.pk,
                items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
                processed_by_user_id=admin_user.pk,
                refund_method=Return.RefundMethod.CASH,
            )


@pytest.mark.django_db
class TestCalculateRefundAmount:
    def test_calculate_refund_amount(self, completed_order, admin_user):
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[
                {'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '75.00'},
            ],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        assert ReturnService.calculate_refund_amount(ret.pk) == Decimal('75.00')


@pytest.mark.django_db
class TestProcessRefund:
    def test_process_cash_refund(self, completed_order, admin_user):
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        processed = ReturnService.process_refund(ret.pk)
        assert processed.status == Return.Status.COMPLETED
        assert processed.refund_status == Return.RefundStatus.COMPLETED
        assert processed.completed_at is not None

    def test_process_card_refund(self, completed_order, admin_user):
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CARD,
        )
        processed = ReturnService.process_refund(ret.pk)
        assert processed.status == Return.Status.PROCESSING
        assert processed.refund_status == Return.RefundStatus.PENDING

    def test_process_creates_status_history(self, completed_order, admin_user):
        item = completed_order._test_item
        ret = ReturnService.create_return(
            order_id=completed_order.pk,
            items=[{'order_item_id': item.pk, 'quantity': 1, 'refund_amount': '100.00'}],
            processed_by_user_id=admin_user.pk,
            refund_method=Return.RefundMethod.CASH,
        )
        ReturnService.process_refund(ret.pk)
        assert ReturnStatus.objects.filter(return_obj=ret).count() == 2
