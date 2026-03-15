"""Тесты API синхронизации склада и ERP."""

import pytest
from rest_framework.test import APIClient


WAREHOUSE_URL = "/api/v1/admin/sync/warehouse/"
ERP_URL = "/api/v1/admin/sync/erp/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    from accounts.models import User

    return User.objects.create_user(username="regular", password="testpass123")


@pytest.fixture
def admin_user(db):
    from accounts.models import Role, User

    user = User.objects.create_user(username="admin", password="testpass123")
    role, _ = Role.objects.get_or_create(codename="admin", defaults={"name": "Admin", "is_active": True})
    user.roles.add(role)
    return user


@pytest.fixture
def admin_client(api_client, admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def regular_client(api_client, regular_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(regular_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ---------------------------------------------------------------------------
# Warehouse sync
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_warehouse_sync_as_admin(admin_client):
    """POST /sync/warehouse/ → 200 {"status": "ok", "synced": 0}."""
    response = admin_client.post(WAREHOUSE_URL, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert response.data["synced"] == 0


@pytest.mark.django_db
def test_warehouse_sync_requires_auth(api_client):
    """Без JWT → 401."""
    response = api_client.post(WAREHOUSE_URL, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_warehouse_sync_requires_admin_role(regular_client):
    """Обычный пользователь → 403."""
    response = regular_client.post(WAREHOUSE_URL, format="json")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# ERP sync
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_erp_sync_as_admin(admin_client):
    """POST /sync/erp/ → 200 {"status": "ok"}."""
    response = admin_client.post(ERP_URL, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "ok"


@pytest.mark.django_db
def test_erp_sync_requires_auth(api_client):
    """Без JWT → 401."""
    response = api_client.post(ERP_URL, format="json")
    assert response.status_code == 401


@pytest.mark.django_db
def test_erp_sync_requires_admin_role(regular_client):
    """Обычный пользователь → 403."""
    response = regular_client.post(ERP_URL, format="json")
    assert response.status_code == 403
