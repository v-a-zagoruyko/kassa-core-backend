import decimal

import pytest

from common.models import Address
from stores.models import Store, Kiosk
from products.models import Category, Product
from orders.models import Order, OrderItem, OrderStatus


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def address(db):
    return Address.objects.create(city="Тюмень", street="Ленина", house="1")


@pytest.fixture
def store(address):
    return Store.objects.create(name="Тестовая точка", address=address)


@pytest.fixture
def kiosk(store):
    return Kiosk.objects.create(store=store, kiosk_number="001")


@pytest.fixture
def category():
    return Category.objects.create(name="Тестовая категория")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Тестовый товар",
        category=category,
        price=decimal.Decimal("100.00"),
    )


@pytest.fixture
def order(store):
    return Order.objects.create(store=store, total_amount="200.00", final_amount="200.00")


# ---------------------------------------------------------------------------
# Order tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_order_created_with_draft_status(store):
    order = Order.objects.create(store=store)
    assert order.status == Order.Status.DRAFT


@pytest.mark.django_db
def test_order_str(store):
    order = Order.objects.create(store=store)
    assert "Черновик" in str(order)
    assert str(order.id) in str(order)


@pytest.mark.django_db
def test_order_status_transition(store):
    order = Order.objects.create(store=store)
    assert order.status == Order.Status.DRAFT

    order.status = Order.Status.PENDING_PAYMENT
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.PENDING_PAYMENT

    order.status = Order.Status.PAID
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.PAID

    order.status = Order.Status.COMPLETED
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.COMPLETED

    order.status = Order.Status.CANCELLED
    order.save()
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED


@pytest.mark.django_db
def test_order_with_kiosk(store, kiosk):
    order = Order.objects.create(store=store, kiosk=kiosk)
    assert order.kiosk == kiosk


@pytest.mark.django_db
def test_order_kiosk_optional(store):
    order = Order.objects.create(store=store)
    assert order.kiosk is None


@pytest.mark.django_db
def test_order_payment_method_choices(store):
    order = Order.objects.create(
        store=store,
        payment_method=Order.PaymentMethod.CARD,
    )
    assert order.payment_method == Order.PaymentMethod.CARD


@pytest.mark.django_db
def test_order_amounts(store):
    order = Order.objects.create(
        store=store,
        total_amount=decimal.Decimal("500.00"),
        discount_amount=decimal.Decimal("50.00"),
        final_amount=decimal.Decimal("450.00"),
    )
    assert order.total_amount == decimal.Decimal("500.00")
    assert order.discount_amount == decimal.Decimal("50.00")
    assert order.final_amount == decimal.Decimal("450.00")


# ---------------------------------------------------------------------------
# OrderItem tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_order_item_created(order, product):
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=decimal.Decimal("100.00"),
        subtotal=decimal.Decimal("200.00"),
    )
    assert item.quantity == 2
    assert item.subtotal == decimal.Decimal("200.00")


@pytest.mark.django_db
def test_order_item_str(order, product):
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=3,
        price=decimal.Decimal("100.00"),
        subtotal=decimal.Decimal("300.00"),
    )
    assert product.name in str(item)
    assert "3" in str(item)


@pytest.mark.django_db
def test_order_items_relation(order, product):
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=decimal.Decimal("100.00"),
        subtotal=decimal.Decimal("100.00"),
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=decimal.Decimal("100.00"),
        subtotal=decimal.Decimal("200.00"),
    )
    assert order.items.count() == 2


@pytest.mark.django_db
def test_order_item_marking_code_default_empty(order, product):
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=decimal.Decimal("50.00"),
        subtotal=decimal.Decimal("50.00"),
    )
    assert item.marking_code == ""


@pytest.mark.django_db
def test_order_item_cascade_delete(order, product):
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=decimal.Decimal("100.00"),
        subtotal=decimal.Decimal("100.00"),
    )
    order_id = order.id
    order.hard_delete()
    assert OrderItem.objects.filter(order_id=order_id).count() == 0


# ---------------------------------------------------------------------------
# OrderStatus tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_order_status_history_created(order):
    entry = OrderStatus.objects.create(
        order=order,
        status=Order.Status.DRAFT,
    )
    assert entry.status == Order.Status.DRAFT
    assert entry.comment == ""


@pytest.mark.django_db
def test_order_status_str(order):
    entry = OrderStatus.objects.create(
        order=order,
        status=Order.Status.PENDING_PAYMENT,
    )
    assert "Ожидает оплаты" in str(entry)


@pytest.mark.django_db
def test_order_status_history_relation(order):
    OrderStatus.objects.create(order=order, status=Order.Status.DRAFT)
    OrderStatus.objects.create(order=order, status=Order.Status.PENDING_PAYMENT)
    OrderStatus.objects.create(order=order, status=Order.Status.PAID)

    history = list(order.status_history.all())
    assert len(history) == 3
    # Ordering by created_at — first should be DRAFT
    assert history[0].status == Order.Status.DRAFT


@pytest.mark.django_db
def test_order_status_cascade_delete(order):
    OrderStatus.objects.create(order=order, status=Order.Status.DRAFT)
    order_id = order.id
    order.hard_delete()
    assert OrderStatus.objects.filter(order_id=order_id).count() == 0


@pytest.mark.django_db
def test_order_status_with_comment(order):
    entry = OrderStatus.objects.create(
        order=order,
        status=Order.Status.CANCELLED,
        comment="Отменён по просьбе клиента",
    )
    assert entry.comment == "Отменён по просьбе клиента"
