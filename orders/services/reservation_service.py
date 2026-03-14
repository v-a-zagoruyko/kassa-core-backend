"""ReservationService — управление резервированием товаров для заказов."""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from common.exceptions import DomainValidationError

logger = logging.getLogger(__name__)

RESERVATION_TTL_MINUTES = 15


class InsufficientStockError(DomainValidationError):
    """Недостаточно товара на складе для резервирования."""

    def __init__(self, product_name: str, requested: float, available: float):
        self.product_name = product_name
        self.requested = requested
        self.available = available
        super().__init__(
            f"Недостаточно товара «{product_name}»: запрошено {requested}, доступно {available}"
        )


class ReservationService:
    @staticmethod
    @transaction.atomic
    def reserve_products(order_id) -> list:
        """
        Резервировать товары для заказа.

        Для каждого OrderItem создаёт Reservation с expires_at = now + 15 минут.
        Атомарно блокирует Stock через select_for_update, проверяет available_quantity.
        При нехватке — rollback + InsufficientStockError.

        Returns:
            list[Reservation]: список созданных резервов.
        """
        from orders.models import Order, Reservation
        from products.models import Stock

        order = Order.objects.select_related("store").get(id=order_id)
        items = list(order.items.select_related("product").all())

        if not items:
            logger.warning("order %s has no items to reserve", order_id)
            return []

        expires_at = timezone.now() + timedelta(minutes=RESERVATION_TTL_MINUTES)
        reservations = []

        for item in items:
            # Блокируем строку Stock атомарно
            stock = (
                Stock.objects.select_for_update()
                .filter(product=item.product, store=order.store)
                .first()
            )

            if stock is None:
                raise InsufficientStockError(
                    product_name=item.product.name,
                    requested=float(item.quantity),
                    available=0,
                )

            available = float(stock.available_quantity)
            requested = float(item.quantity)

            if available < requested:
                raise InsufficientStockError(
                    product_name=item.product.name,
                    requested=requested,
                    available=available,
                )

            # Увеличиваем reserved_quantity
            stock.reserved_quantity += item.quantity
            stock.save(update_fields=["reserved_quantity", "updated_at"])

            reservation = Reservation.objects.create(
                order=order,
                product=item.product,
                store=order.store,
                quantity=item.quantity,
                expires_at=expires_at,
                status=Reservation.Status.ACTIVE,
            )
            reservations.append(reservation)
            logger.info(
                "Reserved %s x%s for order %s (reservation %s)",
                item.product.name,
                item.quantity,
                order_id,
                reservation.id,
            )

        return reservations

    @staticmethod
    @transaction.atomic
    def release_reservation(reservation_id) -> None:
        """
        Освободить резерв: статус → released, вернуть quantity в Stock.
        """
        from orders.models import Reservation
        from products.models import Stock

        reservation = Reservation.objects.select_for_update().get(id=reservation_id)

        if reservation.status != Reservation.Status.ACTIVE:
            logger.warning(
                "Reservation %s is not active (status=%s), skip release",
                reservation_id,
                reservation.status,
            )
            return

        # Возвращаем сток
        stock = Stock.objects.select_for_update().get(
            product=reservation.product,
            store=reservation.store,
        )
        stock.reserved_quantity = max(
            stock.reserved_quantity - reservation.quantity, 0
        )
        stock.save(update_fields=["reserved_quantity", "updated_at"])

        reservation.status = Reservation.Status.RELEASED
        reservation.released_at = timezone.now()
        reservation.save(update_fields=["status", "released_at", "updated_at"])

        logger.info("Released reservation %s", reservation_id)

    @staticmethod
    def release_order_reservations(order_id) -> None:
        """
        Освободить все активные резервы заказа.
        """
        from orders.models import Reservation

        active_reservations = Reservation.objects.filter(
            order_id=order_id,
            status=Reservation.Status.ACTIVE,
        )

        for reservation in active_reservations:
            ReservationService.release_reservation(reservation.id)

        logger.info("Released all reservations for order %s", order_id)

    @staticmethod
    @transaction.atomic
    def complete_reservation(reservation_id) -> None:
        """
        Завершить резерв (при успешной оплате): статус → completed.
        Резерв снимается — списываем со стока окончательно.
        """
        from orders.models import Reservation
        from products.models import Stock

        reservation = Reservation.objects.select_for_update().get(id=reservation_id)

        if reservation.status != Reservation.Status.ACTIVE:
            logger.warning(
                "Reservation %s is not active (status=%s), skip complete",
                reservation_id,
                reservation.status,
            )
            return

        # Уменьшаем quantity и reserved_quantity (товар списан)
        stock = Stock.objects.select_for_update().get(
            product=reservation.product,
            store=reservation.store,
        )
        stock.quantity = max(stock.quantity - reservation.quantity, 0)
        stock.reserved_quantity = max(
            stock.reserved_quantity - reservation.quantity, 0
        )
        stock.save(update_fields=["quantity", "reserved_quantity", "updated_at"])

        reservation.status = Reservation.Status.COMPLETED
        reservation.save(update_fields=["status", "updated_at"])

        logger.info("Completed reservation %s", reservation_id)
