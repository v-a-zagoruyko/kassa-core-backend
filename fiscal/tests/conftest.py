"""Фикстуры для тестов фискального домена."""

import threading
import pytest
from django.test.utils import setup_databases, teardown_databases


SQLITE_DB = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
    "ATOMIC_REQUESTS": False,
    "AUTOCOMMIT": True,
    "CONN_MAX_AGE": 0,
    "CONN_HEALTH_CHECKS": False,
    "OPTIONS": {},
    "TIME_ZONE": None,
    "USER": "",
    "PASSWORD": "",
    "HOST": "",
    "PORT": "",
    "TEST": {
        "CHARSET": None,
        "COLLATION": None,
        "MIGRATE": True,
        "MIRROR": None,
        "NAME": ":memory:",
    },
}


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    """Переопределяет БД на SQLite in-memory для тестов (без Postgres в CI)."""
    from django.conf import settings
    from django.db import connections

    settings.DATABASES["default"] = SQLITE_DB.copy()
    connections._connections = threading.local()

    with django_db_blocker.unblock():
        old_config = setup_databases(verbosity=0, interactive=False)
    yield
    with django_db_blocker.unblock():
        teardown_databases(old_config, verbosity=0)


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def paid_order(db):
    """Создаёт минимальный оплаченный заказ с одной позицией."""
    from django.contrib.auth import get_user_model
    from common.models import Address
    from products.models import Category, Product
    from stores.models import Store
    from orders.models import Order, OrderItem

    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='pass')
    address = Address.objects.create(city='Город', street='Улица', house='1')
    store = Store.objects.create(name='Test Store', address=address)
    category = Category.objects.create(name='Cat', slug='cat')
    product = Product.objects.create(
        name='Товар',
        slug='tovar',
        category=category,
        price='100.00',
    )
    order = Order.objects.create(
        store=store,
        customer=user,
        status=Order.Status.PAID,
        total_amount='100.00',
        final_amount='100.00',
        payment_method=Order.PaymentMethod.CARD,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price='100.00',
        subtotal='100.00',
    )
    return order


@pytest.fixture
def admin_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='admin', password='pass', is_staff=True)
