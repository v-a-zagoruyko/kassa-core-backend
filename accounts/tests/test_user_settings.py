import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User, UserSettings


@pytest.fixture
def user(db):
    return User.objects.create_user(username="settingsuser", password="pass123")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_user_settings_auto_created_on_registration():
    user = User.objects.create_user(username="newuser", password="pass123")
    assert UserSettings.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_user_settings_get_returns_existing(user):
    existing = UserSettings.objects.get(user=user)
    result = UserSettings.get(user)
    assert result.pk == existing.pk


@pytest.mark.django_db
def test_user_settings_get_creates_if_missing(db):
    user = User.objects.create_user(username="nosetuser", password="pass123")
    UserSettings.objects.get(user=user).hard_delete()
    result = UserSettings.get(user)
    assert result.user == user
    assert UserSettings.objects.filter(user=user).exists()


def test_get_settings_returns_200(auth_client):
    response = auth_client.get("/api/v1/accounts/users/me/settings/")
    assert response.status_code == 200
    data = response.json()
    assert "language" in data
    assert "timezone" in data
    assert "notifications_enabled" in data
    assert "theme" in data
    assert "extra" in data


def test_get_settings_default_values(auth_client):
    response = auth_client.get("/api/v1/accounts/users/me/settings/")
    data = response.json()
    assert data["language"] == "ru"
    assert data["timezone"] == "UTC"
    assert data["notifications_enabled"] is True
    assert data["theme"] == "light"
    assert data["extra"] == {}


def test_patch_settings_updates_fields(auth_client):
    response = auth_client.patch(
        "/api/v1/accounts/users/me/settings/",
        {"language": "en", "theme": "dark"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    assert data["theme"] == "dark"
    assert data["timezone"] == "UTC"


def test_patch_settings_partial_update(auth_client, user):
    response = auth_client.patch(
        "/api/v1/accounts/users/me/settings/",
        {"timezone": "Europe/Moscow"},
        format="json",
    )
    assert response.status_code == 200
    settings = UserSettings.objects.get(user=user)
    assert settings.timezone == "Europe/Moscow"
    assert settings.language == "ru"


def test_get_settings_unauthenticated():
    client = APIClient()
    response = client.get("/api/v1/accounts/users/me/settings/")
    assert response.status_code == 401
