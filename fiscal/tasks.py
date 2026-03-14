"""Celery-задачи фискального домена."""

from uuid import UUID

from celery import shared_task


@shared_task
def send_receipt_to_ofd(receipt_id: str) -> None:
    """Celery-задача для асинхронной отправки чека в ОФД."""
    from .services import ReceiptService

    ReceiptService.send_to_ofd(UUID(receipt_id))
