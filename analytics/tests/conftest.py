"""Фикстуры для тестов аналитики."""

import threading
from decimal import Decimal

import pytest
from django.test.utils import setup_databases, teardown_databases


SQLITE_DB = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': ':memory:',
    'ATOMIC_REQUESTS': False,
    'AUTOCOMMIT': True,
    'CONN_MAX_AGE': 0,
    'CONN_HEALTH_CHECKS': False,
    'OPTIONS': {},
    'TIME_ZONE': None,
    'USER': '',
    'PASSWORD': '',
    'HOST': '',
    'PORT': '',
    'TEST': {
        'CHARSET': None,
        'COLLATION': None,
        'MIGRATE': True,
        'MIRROR': None,
        'NAME': ':memory:',
    },
}


@pytest.fixture(scope='session')
def django_db_setup(django_test_environment, django_db_blocker):
    """SQLite in-memory вместо Postgres для тестов."""
    from django.conf import settings
    from django.db import connections

    settings.DATABASES['default'] = SQLITE_DB.copy()
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
def admin_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username='admin_analytics', password='pass', is_staff=True)


@pytest.fixture
def store(db):
    from common.models import Address
    from stores.models import Store
    address = Address.objects.create(city='Город', street='Улица', house='1')
    return Store.objects.create(name='Test Store Analytics', address=address)


@pytest.fixture
def paid_order(db, store):
    """Оплаченный заказ с 2 позициями."""
    from django.contrib.auth import get_user_model
    from products.models import Category, Product
    from orders.models import Order, OrderItem

    User = get_user_model()
    user = User.objects.create_user(username='customer_analytics', password='pass')
    category = Category.objects.create(name='Cat Analytics', slug='cat-analytics')
    product = Product.objects.create(
        name='Товар А',
        slug='tovar-a-analytics',
        category=category,
        price=Decimal('150.00'),
    )
    order = Order.objects.create(
        store=store,
        customer=user,
        status=Order.Status.PAID,
        total_amount=Decimal('300.00'),
        final_amount=Decimal('300.00'),
        payment_method=Order.PaymentMethod.CARD,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=Decimal('150.00'),
        subtotal=Decimal('300.00'),
    )
    return order
