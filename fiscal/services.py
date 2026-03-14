"""Сервисный слой фискального домена."""

import logging
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
