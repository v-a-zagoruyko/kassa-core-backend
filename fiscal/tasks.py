"""Celery-задачи фискального домена."""

import logging
from uuid import UUID

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_receipt_to_ofd(receipt_id: str) -> None:
    """Celery-задача для асинхронной отправки чека в ОФД."""
    from .services import ReceiptService

    ReceiptService.send_to_ofd(UUID(receipt_id))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_return_receipt_to_ofd(self, return_receipt_id: str) -> None:
    """Отправляет чек возврата в ОФД. Retry: 3 попытки, интервал 60 сек."""
    from .models import ReturnReceipt
    from .ofd_client import OFDClient

    try:
        return_receipt = ReturnReceipt.objects.get(pk=return_receipt_id)
    except ReturnReceipt.DoesNotExist:
        logger.error('ReturnReceipt %s не найден', return_receipt_id)
        return

    from .models import Receipt

    if return_receipt.status in (Receipt.Status.CONFIRMED, Receipt.Status.SENT):
        return  # идемпотентность

    try:
        client = OFDClient()
        response = client.send_receipt(return_receipt)

        return_receipt.status = Receipt.Status.SENT
        return_receipt.sent_at = timezone.now()
        return_receipt.ofd_response = response
        if response.get('status') == 'accepted':
            return_receipt.status = Receipt.Status.CONFIRMED
            return_receipt.confirmed_at = timezone.now()
        return_receipt.save()

    except Exception as exc:
        return_receipt.status = Receipt.Status.FAILED
        return_receipt.error_message = str(exc)
        return_receipt.save()
        logger.error('Ошибка отправки чека возврата %s в ОФД: %s', return_receipt_id, exc)
        raise self.retry(exc=exc)
