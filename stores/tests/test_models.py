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


@pytest.mark.django_db
def test_kiosk_create():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин Kiosk",
        address=address,
    )
    kiosk = Kiosk.objects.create(
        store=store,
        name="Касса 1",
    )

    assert str(kiosk) == "Касса 1"


@pytest.mark.django_db
def test_kiosk_serial_number_unique():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин Kiosk 2",
        address=address,
    )
    Kiosk.objects.create(
        store=store,
        name="Касса А",
        serial_number="SN-001",
    )

    with pytest.raises(IntegrityError):
        Kiosk.objects.create(
            store=store,
            name="Касса Б",
            serial_number="SN-001",
        )


@pytest.mark.django_db
def test_store_settings_create():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин Settings",
        address=address,
    )
    setting = StoreSettings.objects.create(
        store=store,
        key="theme",
        value="dark",
    )

    assert str(setting) == f"{store.name} — theme"


@pytest.mark.django_db
def test_store_settings_unique_store_key():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин Settings 2",
        address=address,
    )
    StoreSettings.objects.create(
        store=store,
        key="language",
        value="ru",
    )

    with pytest.raises(IntegrityError):
        StoreSettings.objects.create(
            store=store,
            key="language",
            value="en",
        )
