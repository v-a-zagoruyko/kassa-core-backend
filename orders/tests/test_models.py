import decimal

import pytest
from django.db import IntegrityError

from common.models import Address
from stores.models import Store
from products.models import Category, Product
from orders.models import Order, OrderItem, OrderStatus


def make_store():
    address = Address.objects.create(city="Москва", street="Тверская", house="1")
    return Store.objects.create(name="Тестовый магазин", address=address)


def make_product():
    category = Category.objects.create(name="Тестовая категория")
    return Product.objects.create(
        name="Тестовый товар",
        category=category,
        price=decimal.Decimal("100.00"),
    )


@pytest.mark.django_db
def test_create_order():
    store = make_store()
    order = Order.objects.create(store=store, total_price=decimal.Decimal("0.00"))
    assert order.status == OrderStatus.PENDING


@pytest.mark.django_db
def test_order_item_subtotal():
    store = make_store()
    product = make_product()
    order = Order.objects.create(store=store, total_price=decimal.Decimal("500.00"))
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=3,
        price=decimal.Decimal("150.00"),
    )
    assert item.subtotal == decimal.Decimal("450.00")


@pytest.mark.django_db
def test_order_item_unique_constraint():
    store = make_store()
    product = make_product()
    order = Order.objects.create(store=store, total_price=decimal.Decimal("200.00"))
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=decimal.Decimal("100.00"),
    )
    with pytest.raises(IntegrityError):
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            price=decimal.Decimal("100.00"),
        )
