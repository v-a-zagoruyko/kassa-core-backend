"""
Тест: импорт Celery app не падает и конфигурация корректна.
"""
import pytest


def test_celery_app_import():
    """Импорт celery app работает без ошибок."""
    from kassa_core.celery import app
    assert app is not None
    assert app.main == "kassa_core"


def test_celery_app_from_init():
    """celery_app доступен из kassa_core.__init__."""
    from kassa_core import celery_app
    assert celery_app is not None


@pytest.mark.django_db
def test_celery_settings(settings):
    """CELERY_BROKER_URL задан в настройках."""
    assert hasattr(settings, "CELERY_BROKER_URL")
    assert settings.CELERY_BROKER_URL
    assert hasattr(settings, "CELERY_BEAT_SCHEDULER")
