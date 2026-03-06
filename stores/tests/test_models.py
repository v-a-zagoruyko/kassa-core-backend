import datetime

import pytest
from slugify import slugify
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from common.models import Address
from stores.models import Store, StoreSpecialHours, StoreWorkingHours, Kiosk, StoreSettings


@pytest.mark.django_db
def test_store_clean_validates_delivery_radius():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store(
        name="Магазин 1",
        address=address,
        delivery_radius_km=0,
    )

    with pytest.raises(ValidationError):
        store.clean()


@pytest.mark.django_db
def test_store_save_generates_slug_code():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин Особый",
        address=address,
    )

    assert store.code


@pytest.mark.django_db
def test_store_generate_unique_code_for_same_name():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    first = Store.objects.create(
        name="Магазин Дублирующийся",
        address=address,
    )
    second = Store.objects.create(
        name="Магазин Дублирующийся",
        address=address,
    )

    base_slug = slugify("Магазин Дублирующийся")
    assert first.code == base_slug
    assert second.code.startswith(f"{base_slug}-")


@pytest.mark.django_db
def test_store_working_hours_clean_validates_time_interval():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин 2",
        address=address,
    )

    working_hours = StoreWorkingHours(
        store=store,
        day_of_week=0,
        open_time=datetime.time(18, 0),
        close_time=datetime.time(9, 0),
    )

    with pytest.raises(ValidationError):
        working_hours.clean()


@pytest.mark.django_db
def test_store_special_hours_clean_validates_time_interval():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин 3",
        address=address,
    )

    special_hours = StoreSpecialHours(
        store=store,
        date=datetime.date.today(),
        open_time=datetime.time(18, 0),
        close_time=datetime.time(9, 0),
    )

    with pytest.raises(ValidationError):
        special_hours.clean()


@pytest.mark.django_db
def test_store_working_hours_unique_constraint():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин 4",
        address=address,
    )

    StoreWorkingHours.objects.create(
        store=store,
        day_of_week=0,
        open_time=datetime.time(9, 0),
        close_time=datetime.time(18, 0),
    )

    with pytest.raises(IntegrityError):
        StoreWorkingHours.objects.create(
            store=store,
            day_of_week=0,
            open_time=datetime.time(10, 0),
            close_time=datetime.time(19, 0),
        )


@pytest.mark.django_db
def test_store_special_hours_unique_constraint():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин 5",
        address=address,
    )
    date = datetime.date.today()

    StoreSpecialHours.objects.create(
        store=store,
        date=date,
        open_time=datetime.time(9, 0),
        close_time=datetime.time(18, 0),
    )

    with pytest.raises(IntegrityError):
        StoreSpecialHours.objects.create(
            store=store,
            date=date,
            open_time=datetime.time(10, 0),
            close_time=datetime.time(19, 0),
        )


@pytest.fixture
def store_for_kiosk(db):
    address = Address.objects.create(
        city="Тюмень",
        street="Республики",
        house="1",
    )
    return Store.objects.create(name="Тест-Магазин", address=address)


@pytest.mark.django_db
def test_kiosk_create(store_for_kiosk):
    kiosk = Kiosk.objects.create(store=store_for_kiosk, kiosk_number="K-01")
    assert kiosk.pk is not None
    assert kiosk.is_active is True
    assert str(kiosk) == f"{store_for_kiosk.name} — касса K-01"


@pytest.mark.django_db
def test_kiosk_unique_constraint(store_for_kiosk):
    Kiosk.objects.create(store=store_for_kiosk, kiosk_number="K-01")
    with pytest.raises(IntegrityError):
        Kiosk.objects.create(store=store_for_kiosk, kiosk_number="K-01")


@pytest.mark.django_db
def test_kiosk_unique_constraint_different_stores():
    """Одинаковый kiosk_number в разных магазинах — ОК."""
    address1 = Address.objects.create(city="Тюмень", street="Ленина", house="2")
    address2 = Address.objects.create(city="Тюмень", street="Мира", house="3")
    store_a = Store.objects.create(name="Магазин-А", address=address1)
    store_b = Store.objects.create(name="Магазин-Б", address=address2)
    Kiosk.objects.create(store=store_a, kiosk_number="K-01")
    kiosk = Kiosk.objects.create(store=store_b, kiosk_number="K-01")
    assert kiosk.pk is not None


@pytest.mark.django_db
def test_store_settings_create(store_for_kiosk):
    settings = StoreSettings.objects.create(store=store_for_kiosk)
    assert settings.pk is not None
    assert settings.allow_cash is True
    assert settings.allow_card is True
    assert settings.max_idle_seconds == 120
    assert str(settings) == f"Настройки: {store_for_kiosk.name}"


@pytest.mark.django_db
def test_store_settings_one_to_one_constraint(store_for_kiosk):
    StoreSettings.objects.create(store=store_for_kiosk)
    with pytest.raises(IntegrityError):
        StoreSettings.objects.create(store=store_for_kiosk)

