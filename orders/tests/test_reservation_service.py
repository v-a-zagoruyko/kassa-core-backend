"""
Тесты ReservationService.
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone


@pytest.fixture
def store(db):
    from stores.models import Store
    from common.models import Address
    address = Address.objects.create(city="Тюмень", street="Ленина", house="1")
    return Store.objects.create(name="Test Store", address=address)


@pytest.fixture
def category(db):
    from products.models import Category
    return Category.objects.create(name="Test Category")


@pytest.fixture
def product(db, category):
    from products.models import Product
    return Product.objects.create(name="Test Product", category=category, price=Decimal("100.00"))


@pytest.fixture
def stock(db, product, store):
    from products.models import Stock
    return Stock.objects.create(
        product=product,
        store=store,
        quantity=Decimal("10.000"),
        reserved_quantity=Decimal("0.000"),
    )


@pytest.fixture
def user(db):
    from accounts.models import User
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
    )


@pytest.fixture
def order(db, store, user):
    from orders.models import Order
    return Order.objects.create(
        store=store,
        customer=user,
        status=Order.Status.PENDING_PAYMENT,
    )


@pytest.fixture
def order_item(db, order, product):
    from orders.models import OrderItem
    return OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=Decimal("100.00"),
        subtotal=Decimal("200.00"),
    )


@pytest.mark.django_db(transaction=True)
def test_reserve_products_success(order, order_item, stock):
    """reserve_products создаёт резервы и увеличивает reserved_quantity."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation
    from products.models import Stock

    reservations = ReservationService.reserve_products(order.id)

    assert len(reservations) == 1
    reservation = reservations[0]
    assert reservation.status == Reservation.Status.ACTIVE
    assert reservation.quantity == order_item.quantity
    assert reservation.order == order
    assert reservation.product == order_item.product

    # expires_at должен быть примерно через 15 минут
    now = timezone.now()
    assert now < reservation.expires_at <= now + timedelta(minutes=16)

    # Stock: reserved_quantity увеличился
    stock.refresh_from_db()
    assert stock.reserved_quantity == Decimal("2.000")
    assert stock.available_quantity == Decimal("8.000")


@pytest.mark.django_db(transaction=True)
def test_reserve_products_insufficient_stock(order, order_item, stock):
    """reserve_products поднимает InsufficientStockError при нехватке."""
    from orders.services.reservation_service import ReservationService, InsufficientStockError
    from orders.models import OrderItem

    # Ставим количество больше остатка
    order_item.quantity = 20
    order_item.save()

    with pytest.raises(InsufficientStockError) as exc_info:
        ReservationService.reserve_products(order.id)

    assert "Test Product" in str(exc_info.value)

    # Stock не должен был измениться (rollback)
    stock.refresh_from_db()
    assert stock.reserved_quantity == Decimal("0.000")


@pytest.mark.django_db(transaction=True)
def test_release_reservation(order, order_item, stock):
    """release_reservation возвращает quantity в Stock и меняет статус."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation

    reservations = ReservationService.reserve_products(order.id)
    reservation = reservations[0]

    stock.refresh_from_db()
    assert stock.reserved_quantity == Decimal("2.000")

    ReservationService.release_reservation(reservation.id)

    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.RELEASED
    assert reservation.released_at is not None

    stock.refresh_from_db()
    assert stock.reserved_quantity == Decimal("0.000")


@pytest.mark.django_db(transaction=True)
def test_release_reservation_idempotent(order, order_item, stock):
    """Повторный вызов release_reservation для уже освобождённого резерва — безопасен."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation

    reservations = ReservationService.reserve_products(order.id)
    reservation = reservations[0]

    ReservationService.release_reservation(reservation.id)
    ReservationService.release_reservation(reservation.id)  # second call - should not raise

    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.RELEASED


@pytest.mark.django_db(transaction=True)
def test_release_order_reservations(order, order_item, stock):
    """release_order_reservations освобождает все активные резервы заказа."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation

    ReservationService.reserve_products(order.id)

    ReservationService.release_order_reservations(order.id)

    active_count = Reservation.objects.filter(
        order=order,
        status=Reservation.Status.ACTIVE,
    ).count()
    assert active_count == 0

    stock.refresh_from_db()
    assert stock.reserved_quantity == Decimal("0.000")


@pytest.mark.django_db(transaction=True)
def test_complete_reservation(order, order_item, stock):
    """complete_reservation: статус → completed, товар списывается со стока."""
    from orders.services.reservation_service import ReservationService
    from orders.models import Reservation

    reservations = ReservationService.reserve_products(order.id)
    reservation = reservations[0]

    ReservationService.complete_reservation(reservation.id)

    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.COMPLETED

    stock.refresh_from_db()
    assert stock.quantity == Decimal("8.000")
    assert stock.reserved_quantity == Decimal("0.000")


@pytest.mark.django_db(transaction=True)
def test_release_expired_reservations_task(order, order_item, stock):
    """Задача release_expired_reservations освобождает истёкшие резервы."""
    from orders.models import Reservation
    from orders.tasks import release_expired_reservations

    # Создаём резерв вручную с expires_at в прошлом
    reservation = Reservation.objects.create(
        order=order,
        product=order_item.product,
        store=order.store,
        quantity=Decimal("2.000"),
        expires_at=timezone.now() - timedelta(minutes=1),
        status=Reservation.Status.ACTIVE,
    )
    # Устанавливаем reserved_quantity для теста
    stock.reserved_quantity = Decimal("2.000")
    stock.save()

    count = release_expired_reservations()

    assert count == 1

    reservation.refresh_from_db()
    assert reservation.status == Reservation.Status.RELEASED

    stock.refresh_from_db()
    assert stock.reserved_quantity == Decimal("0.000")
