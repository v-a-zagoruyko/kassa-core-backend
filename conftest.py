import pytest


@pytest.fixture
def api_client(db):
    """
    Базовый DRF-клиент для API-тестов.
    """
    from rest_framework.test import APIClient

    return APIClient()

