"""OrderService — business logic for order lifecycle management."""

import logging
from decimal import Decimal
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

RESERVATION_TTL_MINUTES = 15


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(
        user,
        store_id,
        order_type: str = 'delivery',
        delivery_address_id: Optional[int] = None,
        courier_comment: str = '',
    ):
        """Create a new order in 'draft' status.

        Args:
            user: User instance (customer).
            store_id: UUID of the Store.
            order_type: 'delivery', 'pickup', or 'kiosk'.
            delivery_address_id: Required when order_type == 'delivery'.
            courier_comment: Optional comment from client.

        Returns:
            Order instance.

        Raises:
            ValueError: if delivery_address_id is missing for delivery orders.
        """
        from orders.models import Order
        from stores.services.delivery_zone_service import DeliveryZoneService

        if order_type == 'delivery' and not delivery_address_id:
            raise ValueError('delivery_address_id is required for delivery orders.')

        delivery_cost = Decimal('0')

        if order_type == 'delivery':
            # We don't know exact distance at creation time, use zone with smallest radius
            zones = DeliveryZoneService.get_zone_for_store(store_id)
            if zones.exists():
                delivery_cost = zones.first().delivery_cost

        order = Order.objects.create(
            customer=user,
            store_id=store_id,
            order_type=order_type,
            status=Order.Status.DRAFT,
            delivery_address_id=delivery_address_id,
            delivery_cost=delivery_cost,
            courier_comment=courier_comment,
        )
        logger.info('Order %s created for user %s, type=%s', order.id, getattr(user, 'id', user), order_type)
        return order

    @staticmethod
    @transaction.atomic
    def add_item(order_id, product_id, quantity):
        """Add or update an item in a draft order.

        Args:
            order_id: UUID of the Order.
            product_id: UUID of the Product.
            quantity: int or Decimal quantity to add.

        Returns:
            OrderItem instance.

        Raises:
            ValueError: if order is not in draft status or insufficient stock.
            Order.DoesNotExist / Product.DoesNotExist / Stock.DoesNotExist.
        """
        from orders.models import Order, OrderItem
        from products.models import Product, Stock
        from products.services.stock_service import get_available_quantity

        order = Order.objects.select_for_update().get(pk=order_id)
        if order.status != Order.Status.DRAFT:
            raise ValueError(f'Cannot add items to order with status "{order.status}".')

        product = Product.objects.get(pk=product_id)
        available = get_available_quantity(product, order.store)

        if available < Decimal(str(quantity)):
            raise ValueError(
                f'Insufficient stock for product "{product.name}": '
                f'requested {quantity}, available {available}.'
            )

        # Determine price: try store-specific price, fall back to product.price
        price = _get_product_price(product, order.store)

        item, created = OrderItem.objects.get_or_create(
            order=order,
            product=product,
            defaults={
                'quantity': quantity,
                'price': price,
                'subtotal': price * Decimal(str(quantity)),
            },
        )

        if not created:
            item.quantity = quantity
            item.price = price
            item.subtotal = price * Decimal(str(quantity))
            item.save()

        OrderService.calculate_totals(order_id)
        return item

    @staticmethod
    @transaction.atomic
    def remove_item(order_id, item_id) -> None:
        """Remove an item from a draft order.

        Args:
            order_id: UUID of the Order.
            item_id: UUID of the OrderItem.

        Raises:
            ValueError: if order is not in draft status.
        """
        from orders.models import Order, OrderItem

        order = Order.objects.select_for_update().get(pk=order_id)
        if order.status != Order.Status.DRAFT:
            raise ValueError(f'Cannot remove items from order with status "{order.status}".')

        OrderItem.objects.filter(pk=item_id, order=order).delete()
        OrderService.calculate_totals(order_id)

    @staticmethod
    @transaction.atomic
    def calculate_totals(order_id):
        """Recalculate order total_amount and final_amount.

        total_amount = sum(item.price * quantity)
        final_amount = total_amount - discount_amount + delivery_cost

        Args:
            order_id: UUID of the Order.

        Returns:
            Order instance with updated totals.
        """
        from orders.models import Order

        order = Order.objects.select_for_update().get(pk=order_id)
        items = order.items.all()

        total_amount = sum(
            item.price * Decimal(str(item.quantity))
            for item in items
        ) or Decimal('0')

        final_amount = total_amount - order.discount_amount + order.delivery_cost

        order.total_amount = total_amount
        order.final_amount = max(final_amount, Decimal('0'))
        order.save(update_fields=['total_amount', 'final_amount', 'updated_at'])
        return order

    @staticmethod
    @transaction.atomic
    def submit_order(order_id):
        """Submit a draft order.

        - Validates at least 1 item exists.
        - Validates delivery_address for delivery orders.
        - Creates Reservation for each item (expires_at = now + 15 min).
        - Deducts from Stock.quantity.
        - Transitions Order.status → 'pending'.

        Args:
            order_id: UUID of the Order.

        Returns:
            Order instance.

        Raises:
            ValueError: validation errors.
        """
        from orders.models import Order, Reservation
        from products.models import Stock
        from products.services.stock_service import get_available_quantity

        order = Order.objects.select_for_update().prefetch_related('items').get(pk=order_id)

        if order.status != Order.Status.DRAFT:
            raise ValueError(f'Cannot submit order with status "{order.status}".')

        items = list(order.items.all())
        if not items:
            raise ValueError('Cannot submit an order with no items.')

        if order.order_type == 'delivery' and not order.delivery_address_id:
            raise ValueError('Delivery address is required for delivery orders.')

        expires_at = timezone.now() + timedelta(minutes=RESERVATION_TTL_MINUTES)

        for item in items:
            available = get_available_quantity(item.product, order.store)
            if available < Decimal(str(item.quantity)):
                raise ValueError(
                    f'Insufficient stock for "{item.product.name}": '
                    f'requested {item.quantity}, available {available}.'
                )

            # Create reservation
            Reservation.objects.create(
                order=order,
                product=item.product,
                store=order.store,
                quantity=Decimal(str(item.quantity)),
                expires_at=expires_at,
                status=Reservation.Status.ACTIVE,
            )

            # Deduct from Stock
            try:
                stock = Stock.objects.select_for_update().get(
                    product=item.product, store=order.store
                )
                stock.quantity -= Decimal(str(item.quantity))
                stock.save(update_fields=['quantity', 'updated_at'])
            except Stock.DoesNotExist:
                raise ValueError(
                    f'No stock record found for product "{item.product.name}" in store "{order.store.name}".'
                )

        order.status = Order.Status.PENDING
        order.save(update_fields=['status', 'updated_at'])
        logger.info('Order %s submitted, status → pending', order.id)
        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order_id):
        """Cancel an order and release all reservations.

        - Sets Reservation.status → released, released_at = now.
        - Returns Stock.quantity.
        - Transitions Order.status → 'cancelled'.

        Args:
            order_id: UUID of the Order.

        Returns:
            Order instance.

        Raises:
            ValueError: if order is already completed or cancelled.
        """
        from orders.models import Order, Reservation
        from products.models import Stock

        order = Order.objects.select_for_update().get(pk=order_id)

        if order.status in (Order.Status.COMPLETED, Order.Status.CANCELLED):
            raise ValueError(f'Cannot cancel order with status "{order.status}".')

        now = timezone.now()
        reservations = Reservation.objects.select_for_update().filter(
            order=order,
            status=Reservation.Status.ACTIVE,
        )

        for reservation in reservations:
            # Return stock
            try:
                stock = Stock.objects.select_for_update().get(
                    product=reservation.product, store=reservation.store
                )
                stock.quantity += reservation.quantity
                stock.save(update_fields=['quantity', 'updated_at'])
            except Stock.DoesNotExist:
                logger.warning(
                    'Stock not found for reservation %s during cancellation', reservation.id
                )

            reservation.status = Reservation.Status.RELEASED
            reservation.released_at = now
            reservation.save(update_fields=['status', 'released_at', 'updated_at'])

        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        logger.info('Order %s cancelled', order.id)
        return order


def _get_product_price(product, store) -> Decimal:
    """Get the effective price for a product in a store.

    Falls back to product.price if no store-specific price found.
    """
    from products.models import ProductPrice
    from django.utils import timezone

    today = timezone.now().date()
    try:
        price_obj = (
            ProductPrice.objects.filter(
                product=product,
                store=store,
                is_active=True,
                effective_from__lte=today,
            )
            .filter(models_q_effective_to_none_or_gte(today))
            .order_by('-effective_from')
            .first()
        )
        if price_obj:
            return price_obj.price
    except Exception:
        pass
    return product.price


def models_q_effective_to_none_or_gte(today):
    """Helper Q object for nullable effective_to filter."""
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=today)
