import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def debug_task(self):
    """Отладочная задача для проверки Celery."""
    print(f"Request: {self.request!r}")


@shared_task
def calculate_daily_metrics_task(store_id=None, date_str=None):
    """Расчёт метрик за день. Запускается в 00:00 UTC."""
    logger.info(
        "Daily metrics calculation started: store_id=%s date=%s",
        store_id,
        date_str,
    )
    # Заглушка — реализация в Milestone 3 (analytics app).
    return {"status": "ok", "store_id": store_id, "date": date_str}
