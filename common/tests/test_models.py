import pytest

from accounts.models import User
from common.models import Address


@pytest.mark.django_db
def test_soft_delete_marks_object_deleted():
    user = User.objects.create_user(username="user_soft_delete", password="password123")

    assert user.is_deleted is False
    assert user.deleted_at is None

    user.delete()

    user.refresh_from_db()
    assert user.is_deleted is True
    assert user.deleted_at is not None


@pytest.mark.django_db
def test_restore_resets_soft_delete_flags():
    user = User.objects.create_user(username="user_restore", password="password123")
    user.delete()
    user.refresh_from_db()

    user.restore()
    user.refresh_from_db()

    assert user.is_deleted is False
    assert user.deleted_at is None


@pytest.mark.django_db
def test_hard_delete_removes_object():
    user = User.objects.create_user(username="user_hard_delete", password="password123")

    user_id = user.id
    user.hard_delete()

    assert not User.objects.filter(id=user_id).exists()


@pytest.mark.django_db
def test_address_str_without_apartment():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )

    assert str(address) == "Екатеринбург, Ленина, 10"


@pytest.mark.django_db
def test_address_str_with_apartment():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
        apartment="5",
    )

    assert str(address) == "Екатеринбург, Ленина, 10, кв. 5"

