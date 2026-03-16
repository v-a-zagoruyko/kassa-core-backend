import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
_fiscal_logger = logging.getLogger('fiscal.alerts')

from orders.models import Order
from .models import Return, ReturnItem, ReturnStatus


class ReturnService:

    @staticmethod
    @transaction.atomic
    def create_return(
        order_id,
        items: list[dict],
        processed_by_user_id,
        refund_method: str,
        reason_id=None,
        comment: str = '',
    ) -> Return:
        """
        Создаёт возврат для заказа.

        items: list of {order_item_id, quantity, refund_amount}
        """
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            raise ValueError(f'Заказ {order_id} не найден.')

        if order.status not in (Order.Status.PAID, Order.Status.COMPLETED):
            raise ValueError('Возврат возможен только для оплаченных или завершённых заказов.')

        window = timezone.timedelta(hours=12)
        if order.created_at + window < timezone.now():
            raise ValueError('Возврат возможен только в течение 12 часов с момента создания заказа.')

        active_statuses = (Return.Status.PENDING, Return.Status.PROCESSING)
        if Return.objects.filter(order_id=order_id, status__in=active_statuses).exists():
            raise ValueError('Для этого заказа уже существует активный возврат.')

        total_amount = sum(Decimal(str(item['refund_amount'])) for item in items)

        ret = Return.objects.create(
            order_id=order_id,
            processed_by_id=processed_by_user_id,
            refund_method=refund_method,
            reason_id=reason_id,
            comment=comment,
            total_amount=total_amount,
        )

        for item in items:
            ReturnItem.objects.create(
                return_obj=ret,
                order_item_id=item['order_item_id'],
                quantity=item['quantity'],
                refund_amount=Decimal(str(item['refund_amount'])),
            )

        ReturnStatus.objects.create(
            return_obj=ret,
            status=Return.Status.PENDING,
            changed_by_id=processed_by_user_id,
            comment='Возврат создан.',
        )

        return ret

    @staticmethod
    def calculate_refund_amount(return_id) -> Decimal:
        """Возвращает суммарную сумму возврата по всем позициям."""
        from django.db.models import Sum
        result = ReturnItem.objects.filter(return_obj_id=return_id).aggregate(
            total=Sum('refund_amount')
        )
        return result['total'] or Decimal('0.00')

    @staticmethod
    @transaction.atomic
    def process_refund(return_id) -> Return:
        """
        Обрабатывает выплату по возврату.

        - cash: статус immediately completed
        - card: передаётся во внешнюю систему, статус processing/pending
        """
        try:
            ret = Return.objects.select_for_update().get(pk=return_id)
        except Return.DoesNotExist:
            raise ValueError(f'Возврат {return_id} не найден.')

        if ret.status not in (Return.Status.PENDING, Return.Status.PROCESSING):
            raise ValueError('Возврат уже обработан или отменён.')

        if ret.refund_method == Return.RefundMethod.CASH:
            ret.refund_status = Return.RefundStatus.COMPLETED
            ret.status = Return.Status.COMPLETED
            ret.completed_at = timezone.now()
            comment = 'Наличный возврат выполнен.'
        else:
            ret.refund_status = Return.RefundStatus.PENDING
            ret.status = Return.Status.PROCESSING
            comment = 'Запрос на возврат по карте передан во внешнюю систему.'

        ret.save()

        ReturnStatus.objects.create(
            return_obj=ret,
            status=ret.status,
            changed_by=ret.processed_by,
            comment=comment,
        )

        # Фискализация возврата (обязательно по 54-ФЗ)
        try:
            from fiscal.services import ReceiptService as FiscalService
            return_receipt = FiscalService.generate_return_receipt(return_id=ret.id)
            from fiscal.tasks import send_return_receipt_to_ofd
            send_return_receipt_to_ofd.delay(str(return_receipt.id))
            logger.info(
                'Чек возврата %s инициирован для возврата %s',
                return_receipt.receipt_number, ret.id,
            )
        except Exception as exc:
            _fiscal_logger.critical(
                'ФИСКАЛИЗАЦИЯ ВОЗВРАТА ПРОВАЛЕНА для возврата %s: %s',
                ret.id, exc, exc_info=True,
            )

        return ret
