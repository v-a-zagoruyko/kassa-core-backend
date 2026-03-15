"""Celery задачи для интеграций."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def sync_inventory_from_warehouse(store_id=None):
    """Синхронизация остатков со складом каждые 5 минут."""
    from .warehouse import WarehouseService

    result = WarehouseService().sync_inventory(store_id)
    logger.info("Warehouse inventory sync complete: synced=%d store_id=%s", result["synced"], store_id)
    return result
