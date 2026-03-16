"""Сервисный слой фискального домена."""

import logging
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class ReceiptService:
    """Бизнес-логика для работы с фискальными чеками."""

    @staticmethod
    @transaction.atomic
    def generate_receipt(order_id: UUID):
        """
        Формирует фискальный чек для оплаченного заказа.

        Проверяет, что заказ имеет статус 'paid' и чек ещё не создан.
        Генерирует номер чека, строит fiscal_data по 54-ФЗ,
        создаёт Receipt и ReceiptItem для каждой позиции заказа.

        Raises:
            ValueError: если заказ не оплачен или чек уже существует.
        """
        from orders.models import Order
        from .models import Receipt, ReceiptItem

        order = Order.objects.select_for_update().get(pk=order_id)

        if order.status != Order.Status.PAID:
            raise ValueError(
                f'Нельзя создать чек для заказа со статусом '
                f'"{order.get_status_display()}". Требуется статус "paid".'
            )

        if Receipt.all_objects.filter(order=order).exists():
            raise ValueError(f'Чек для заказа {order_id} уже существует.')

        receipt_number = ReceiptService._generate_receipt_number()

        order_items = list(order.items.select_related('product').all())
        items_data = [
            {
                'name': item.product.name,
                'quantity': item.quantity,
                'price': str(item.price),
                'tax_rate': '20%',
            }
            for item in order_items
        ]

        fiscal_data = {
            'type': 'income',
            'total': str(order.final_amount),
            'items': items_data,
            'payment_method': order.payment_method,
        }

        receipt = Receipt.objects.create(
            order=order,
            receipt_number=receipt_number,
            fiscal_data=fiscal_data,
        )

        for item in order_items:
            ReceiptItem.objects.create(
                receipt=receipt,
                product_name=item.product.name,
                quantity=item.quantity,
                price=item.price,
            )

        logger.info('Создан чек %s для заказа %s', receipt_number, order_id)
        return receipt

    @staticmethod
    def _generate_receipt_number() -> str:
        """
        Генерирует уникальный номер чека в формате RCP-{YYYYMMDD}-{NNNNNN}.

        Должен вызываться внутри transaction.atomic с select_for_update,
        чтобы избежать гонки при параллельных запросах.
        """
        from .models import Receipt

        date_str = timezone.now().strftime('%Y%m%d')
        prefix = f'RCP-{date_str}-'
        existing_count = (
            Receipt.all_objects
            .select_for_update()
            .filter(receipt_number__startswith=prefix)
            .count()
        )
        return f'{prefix}{str(existing_count + 1).zfill(6)}'

    @staticmethod
    @transaction.atomic
    def generate_return_receipt(return_id: UUID):
        """
        Формирует чек возврата прихода (54-ФЗ, признак расчёта = 2).
        """
        from returns.models import Return
        from .models import ReturnReceipt, ReturnReceiptItem

        ret = Return.objects.select_for_update().prefetch_related(
            'items__order_item__product'
        ).select_related('order').get(pk=return_id)

        if ReturnReceipt.objects.filter(return_obj=ret).exists():
            raise ValueError(f'Чек возврата для возврата {return_id} уже существует.')

        # Получить оригинальный чек продажи
        original_receipt = None
        try:
            original_receipt = ret.order.receipt
        except Exception:
            pass

        receipt_number = ReceiptService._generate_return_receipt_number()

        items_data = []
        for return_item in ret.items.all():
            product_name = return_item.order_item.product.name
            quantity = return_item.quantity
            unit_price = (return_item.refund_amount / quantity).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            items_data.append({
                'name': product_name,
                'quantity': quantity,
                'price': str(unit_price),
                'tax_rate': '20%',
            })

        fiscal_data = {
            'type': 'return_income',  # признак расчёта = 2 (Возврат прихода)
            'total': str(ret.total_amount),
            'items': items_data,
            'refund_method': ret.refund_method,
            'original_receipt_number': original_receipt.receipt_number if original_receipt else None,
        }

        return_receipt = ReturnReceipt.objects.create(
            return_obj=ret,
            original_receipt=original_receipt,
            receipt_number=receipt_number,
            fiscal_data=fiscal_data,
        )

        for return_item in ret.items.all():
            product_name = return_item.order_item.product.name
            quantity = return_item.quantity
            unit_price = (return_item.refund_amount / quantity).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            ReturnReceiptItem.objects.create(
                receipt=return_receipt,
                product_name=product_name,
                quantity=quantity,
                price=unit_price,
            )

        logger.info('Создан чек возврата %s для возврата %s', receipt_number, return_id)
        return return_receipt

    @staticmethod
    def _generate_return_receipt_number() -> str:
        """Генерирует уникальный номер чека возврата формата RET-YYYYMMDD-NNNNNN."""
        from .models import ReturnReceipt

        today = timezone.now().date()
        prefix = f"RET-{today.strftime('%Y%m%d')}-"
        last = (
            ReturnReceipt.objects.select_for_update()
            .filter(receipt_number__startswith=prefix)
            .order_by('-receipt_number')
            .first()
        )
        if last:
            seq = int(last.receipt_number.split('-')[-1]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:06d}"

    @staticmethod
    def send_to_ofd(receipt_id: UUID) -> None:
        """
        Отправляет чек в ОФД.

        При успехе переводит статус чека в 'sent', записывает sent_at.
        При ошибке переводит в 'failed' и сохраняет error_message.
        В обоих случаях создаёт запись OFDResponse с результатом запроса.
        """
        from .models import OFDResponse, Receipt
        from .ofd_client import OFDClient

        receipt = Receipt.objects.get(pk=receipt_id)

        try:
            client = OFDClient()
            response = client.send_receipt(receipt)

            receipt.status = Receipt.Status.SENT
            receipt.sent_at = timezone.now()
            receipt.error_message = None
            receipt.save(update_fields=['status', 'sent_at', 'error_message', 'updated_at'])

            OFDResponse.objects.create(
                receipt=receipt,
                response_data=response,
                status_code=200,
            )
            logger.info('Чек %s успешно отправлен в ОФД', receipt.receipt_number)

        except Exception as exc:
            error_msg = str(exc)
            receipt.status = Receipt.Status.FAILED
            receipt.error_message = error_msg
            receipt.save(update_fields=['status', 'error_message', 'updated_at'])

            OFDResponse.objects.create(
                receipt=receipt,
                response_data={},
                error_message=error_msg,
            )
            logger.error(
                'Ошибка отправки чека %s в ОФД: %s',
                receipt.receipt_number,
                error_msg,
            )
            raise

    @staticmethod
    def handle_ofd_response(receipt_id: UUID, response: dict) -> None:
        """
        Обрабатывает входящий ответ от ОФД (вызывается через webhook).

        При status='confirmed': переводит чек в 'confirmed', фиксирует confirmed_at.
        При status='failed': переводит в 'failed', сохраняет error_message.
        В обоих случаях создаёт запись OFDResponse.
        """
        from .models import OFDResponse, Receipt

        receipt = Receipt.objects.get(pk=receipt_id)
        incoming_status = response.get('status')

        OFDResponse.objects.create(
            receipt=receipt,
            response_data=response.get('response_data', {}),
            status_code=response.get('status_code'),
            error_message=response.get('error_message'),
        )

        if incoming_status == 'confirmed':
            receipt.status = Receipt.Status.CONFIRMED
            receipt.confirmed_at = timezone.now()
            receipt.ofd_response = response
            receipt.save(update_fields=['status', 'confirmed_at', 'ofd_response', 'updated_at'])
            logger.info('Чек %s подтверждён ОФД', receipt.receipt_number)

        elif incoming_status == 'failed':
            receipt.status = Receipt.Status.FAILED
            receipt.error_message = response.get('error_message', '')
            receipt.ofd_response = response
            receipt.save(update_fields=['status', 'error_message', 'ofd_response', 'updated_at'])
            logger.warning(
                'Чек %s отклонён ОФД: %s',
                receipt.receipt_number,
                receipt.error_message,
            )
