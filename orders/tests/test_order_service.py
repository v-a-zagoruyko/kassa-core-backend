"""Tests for OrderService."""

import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from common.models import Address
from orders.models import Order, OrderItem, Reservation
from orders.services.order_service import OrderService
from products.models import Category, Product, Stock
from stores.models import Store


@pytest.fixture
def address(db):
    return Address.objects.create(city='Тюмень', street='Ленина', house='1')


@pytest.fixture
def store(db, address):
    return Store.objects.create(name='Test Store', address=address)


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name='Категория')


@pytest.fixture
def product(db, category):
    return Product.objects.create(
        name='Товар',
        category=category,
        price=Decimal('200.00'),
    )


@pytest.fixture
def stock(db, product, store):
    return Stock.objects.create(
        product=product,
        store=store,
        quantity=Decimal('10.000'),
    )


@pytest.fixture
def delivery_address(db):
    return Address.objects.create(city='Тюмень', street='Мира', house='5', apartment='10')


@pytest.mark.django_db
class TestCreateOrder:
    def test_create_pickup_order(self, user, store):
        order = OrderService.create_order(user, store.id, order_type='pickup')
        assert order.status == Order.Status.DRAFT
        assert order.order_type == 'pickup'
        assert order.customer == user
        assert order.store == store

    def test_create_delivery_order_requires_address(self, user, store):
        with pytest.raises(ValueError, match='delivery_address_id'):
            OrderService.create_order(user, store.id, order_type='delivery')

    def test_create_delivery_order_with_address(self, user, store, delivery_address):
        order = OrderService.create_order(
            user, store.id,
            order_type='delivery',
            delivery_address_id=delivery_address.id,
        )
        assert order.delivery_address_id == delivery_address.id
        assert order.order_type == 'delivery'


@pytest.mark.django_db
class TestAddItem:
    def test_add_item_to_draft(self, user, store, product, stock):
        order = OrderService.create_order(user, store.id, order_type='pickup')
        item = OrderService.add_item(order.id, product.id, 2)
        assert item.quantity == 2
        assert item.price == product.price
        assert item.subtotal == product.price * 2

        order.refresh_from_db()
        assert order.total_amount == product.price * 2

    def test_update_existing_item(self, user, store, product, stock):
        order = OrderService.create_order(user, store.id, order_type='pickup')
        OrderService.add_item(order.id, product.id, 2)
        OrderService.add_item(order.id, product.id, 5)

        items = order.items.all()
        assert items.count() == 1
        assert items.first().quantity == 5

    def test_insufficient_stock(self, user, store, product, stock):
        order = OrderService.create_order(user, store.id, order_type='pickup')
        with pytest.raises(ValueError, match='Insufficient stock'):
            OrderService.add_item(order.id, product.id, 100)

    def test_cannot_add_to_non_draft(self, user, store, product, stock):
        order = Order.objects.create(store=store, status=Order.Status.PENDING)
        with pytest.raises(ValueError, match='Cannot add items'):
            OrderService.add_item(order.id, product.id, 1)


@pytest.mark.django_db
class TestRemoveItem:
    def test_remove_item(self, user, store, product, stock):
        order = OrderService.create_order(user, store.id, order_type='pickup')
        item = OrderService.add_item(order.id, product.id, 2)
        OrderService.remove_item(order.id, item.id)

        assert order.items.count() == 0
        order.refresh_from_db()
        assert order.total_amount == Decimal('0')


@pytest.mark.django_db
class TestSubmitOrder:
    def test_submit_order_creates_reservation(self, user, store, product, stock, delivery_address):
        order = OrderService.create_order(
            user, store.id, order_type='delivery',
            delivery_address_id=delivery_address.id,
        )
        OrderService.add_item(order.id, product.id, 2)
        submitted = OrderService.submit_order(order.id)

        assert submitted.status == Order.Status.PENDING

        reservation = Reservation.objects.get(order=order, product=product)
        assert reservation.status == Reservation.Status.ACTIVE
        assert reservation.quantity == Decimal('2.000')
        # expires_at ~15 minutes from now
        assert reservation.expires_at > timezone.now()
        assert reservation.expires_at < timezone.now() + timedelta(minutes=16)

    def test_submit_deducts_stock(self, user, store, product, stock, delivery_address):
        initial_qty = stock.quantity
        order = OrderService.create_order(
            user, store.id, order_type='delivery',
            delivery_address_id=delivery_address.id,
        )
        OrderService.add_item(order.id, product.id, 3)
        OrderService.submit_order(order.id)

        stock.refresh_from_db()
        assert stock.quantity == initial_qty - Decimal('3')

    def test_submit_empty_order_fails(self, user, store):
        order = OrderService.create_order(user, store.id, order_type='pickup')
        with pytest.raises(ValueError, match='no items'):
            OrderService.submit_order(order.id)

    def test_submit_delivery_without_address_fails(self, user, store):
        order = Order.objects.create(store=store, order_type='delivery', status='draft')
        OrderItem.objects.create(
            order=order,
            product=Product.objects.first() or Product.objects.create(
                name='P', category=Category.objects.first() or Category.objects.create(name='C'),
                price=Decimal('10'),
            ),
            quantity=1, price=Decimal('10'), subtotal=Decimal('10'),
        )
        with pytest.raises(ValueError, match='Delivery address'):
            OrderService.submit_order(order.id)


@pytest.mark.django_db
class TestCancelOrder:
    def test_cancel_releases_reservations(self, user, store, product, stock, delivery_address):
        initial_qty = stock.quantity
        order = OrderService.create_order(
            user, store.id, order_type='delivery',
            delivery_address_id=delivery_address.id,
        )
        OrderService.add_item(order.id, product.id, 2)
        OrderService.submit_order(order.id)

        # Verify stock was deducted
        stock.refresh_from_db()
        assert stock.quantity == initial_qty - Decimal('2')

        # Cancel
        cancelled = OrderService.cancel_order(order.id)
        assert cancelled.status == Order.Status.CANCELLED

        # Stock restored
        stock.refresh_from_db()
        assert stock.quantity == initial_qty

        # Reservation released
        reservation = Reservation.objects.get(order=order, product=product)
        assert reservation.status == Reservation.Status.RELEASED
        assert reservation.released_at is not None

    def test_cancel_already_cancelled_fails(self, user, store):
        order = Order.objects.create(store=store, status=Order.Status.CANCELLED)
        with pytest.raises(ValueError, match='cancelled'):
            OrderService.cancel_order(order.id)

    def test_cancel_completed_fails(self, user, store):
        order = Order.objects.create(store=store, status=Order.Status.COMPLETED)
        with pytest.raises(ValueError, match='completed'):
            OrderService.cancel_order(order.id)
