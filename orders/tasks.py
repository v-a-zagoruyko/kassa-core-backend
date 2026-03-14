"""Celery-задачи для модуля orders."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="orders.tasks.release_expired_reservations", ignore_result=True)
def release_expired_reservations():
    """
    Найти все истёкшие активные резервы и освободить их.
    Запускается каждую минуту через Celery Beat.
    """
    from orders.models import Reservation
    from orders.services.reservation_service import ReservationService

    expired = list(
        Reservation.objects.filter(
            status=Reservation.Status.ACTIVE,
            expires_at__lt=timezone.now(),
        ).values_list("id", flat=True)
    )

    if not expired:
        logger.debug("No expired reservations found")
        return

    logger.info("Releasing %d expired reservations", len(expired))

    for reservation_id in expired:
        try:
            ReservationService.release_reservation(reservation_id)
        except Exception as exc:
            logger.exception(
                "Failed to release reservation %s: %s", reservation_id, exc
            )

    return len(expired)
