import pytest
from django.core.exceptions import ValidationError

from accounts.models import User, UserSettings


@pytest.mark.django_db
def test_user_manager_create_user_requires_username():
    with pytest.raises(ValueError):
        User.objects.create_user(username="", password="password123")


@pytest.mark.django_db
def test_user_manager_create_user_hashes_password():
    user = User.objects.create_user(username="testuser", password="password123")

    assert user.username == "testuser"
    assert user.check_password("password123")


@pytest.mark.django_db
def test_user_manager_create_superuser_flags():
    user = User.objects.create_superuser(username="admin", password="password123")

    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
def test_user_manager_create_superuser_requires_flags():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            username="admin", password="password123", is_staff=False
        )

    with pytest.raises(ValueError):
        User.objects.create_superuser(
            username="admin2", password="password123", is_superuser=False
        )


@pytest.mark.django_db
def test_user_full_name_property():
    user = User.objects.create_user(
        username="user1",
        password="password123",
        first_name="Иван",
        last_name="Иванов",
    )

    assert user.full_name == "Иван Иванов"


@pytest.mark.django_db
def test_user_full_name_omits_empty_parts():
    user = User.objects.create_user(
        username="user2",
        password="password123",
        first_name="Иван",
        last_name="",
    )

    assert user.full_name == "Иван"


@pytest.mark.django_db
def test_user_settings_created_by_signal():
    user = User.objects.create_user(username="user3", password="password123")

    assert UserSettings.objects.filter(user=user).exists()

