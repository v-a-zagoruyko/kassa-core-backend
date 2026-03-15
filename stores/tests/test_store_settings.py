"""Tests for StoreSettings and related models."""

import pytest

from common.models import Address
from stores.models import Kiosk, Store, StoreSettings


@pytest.fixture
def address(db):
    return Address.objects.create(city="Тюмень", street="Ленина", house="1")


@pytest.fixture
def store(address):
    return Store.objects.create(name="Настройки Магазин", address=address)


# ---------------------------------------------------------------------------
# StoreSettings
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStoreSettings:
    def test_create_with_defaults(self, store):
        settings = StoreSettings.objects.create(store=store)
        assert settings.allow_cash is True
        assert settings.allow_card is True
        assert settings.max_idle_seconds == 120
        assert settings.receipt_header == ""
        assert settings.receipt_footer == ""

    def test_str_representation(self, store):
        settings = StoreSettings.objects.create(store=store)
        assert store.name in str(settings)

    def test_one_to_one_constraint(self, store):
        from django.db import IntegrityError
        StoreSettings.objects.create(store=store)
        with pytest.raises(IntegrityError):
            StoreSettings.objects.create(store=store)

    def test_custom_receipt_header_footer(self, store):
        settings = StoreSettings.objects.create(
            store=store,
            receipt_header="Добро пожаловать",
            receipt_footer="Спасибо за покупку!",
        )
        assert settings.receipt_header == "Добро пожаловать"
        assert settings.receipt_footer == "Спасибо за покупку!"

    def test_disable_cash(self, store):
        settings = StoreSettings.objects.create(store=store, allow_cash=False)
        assert settings.allow_cash is False
        assert settings.allow_card is True

    def test_max_idle_seconds_custom(self, store):
        settings = StoreSettings.objects.create(store=store, max_idle_seconds=60)
        assert settings.max_idle_seconds == 60


# ---------------------------------------------------------------------------
# Kiosk model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestKioskModel:
    def test_create_kiosk(self, store):
        kiosk = Kiosk.objects.create(store=store, kiosk_number="01")
        assert kiosk.is_active is True
        assert kiosk.store == store

    def test_str_representation(self, store):
        kiosk = Kiosk.objects.create(store=store, kiosk_number="02")
        assert store.name in str(kiosk)
        assert "02" in str(kiosk)

    def test_soft_delete(self, store):
        kiosk = Kiosk.objects.create(store=store, kiosk_number="03")
        kiosk_id = kiosk.id
        kiosk.delete()

        assert Kiosk.objects.filter(id=kiosk_id).count() == 0
        assert Kiosk.all_objects.filter(id=kiosk_id).count() == 1

    def test_multiple_kiosks_per_store(self, store):
        Kiosk.objects.create(store=store, kiosk_number="A1")
        Kiosk.objects.create(store=store, kiosk_number="A2")
        assert Kiosk.objects.filter(store=store).count() == 2

    def test_unique_kiosk_number_per_store(self, store):
        from django.db import IntegrityError
        Kiosk.objects.create(store=store, kiosk_number="DUP")
        with pytest.raises(IntegrityError):
            Kiosk.objects.create(store=store, kiosk_number="DUP")
