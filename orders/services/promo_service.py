"""Service for applying promo codes to orders."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone


class PromoService:
    @staticmethod
    def apply_promo(order_id, code: str) -> dict:
        """Apply a promo code to an order.

        Args:
            order_id: UUID of the order.
            code: Promo code string.

        Returns:
            dict with keys: discount_amount, new_final_amount

        Raises:
            ValueError: If the promo code is invalid or cannot be applied.
        """
        from orders.models import Order, PromoCode

        try:
            promo = PromoCode.objects.get(code=code)
        except PromoCode.DoesNotExist:
            raise ValueError('Промокод не найден.')

        order = Order.objects.get(pk=order_id)

        # Validation
        now = timezone.now()

        if not promo.is_active:
            raise ValueError('Промокод неактивен.')

        if now < promo.valid_from:
            raise ValueError('Промокод ещё не действует.')

        if now > promo.valid_until:
            raise ValueError('Срок действия промокода истёк.')

        if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
            raise ValueError('Лимит использований промокода исчерпан.')

        if order.total_amount < promo.min_order_amount:
            raise ValueError(
                f'Минимальная сумма заказа для этого промокода: {promo.min_order_amount} руб.'
            )

        if promo.order_types != promo.OrderTypes.ALL and promo.order_types != order.order_type:
            raise ValueError(
                f'Промокод действует только для типа "{promo.get_order_types_display()}".'
            )

        # Calculate discount
        discount_amount = promo.calculate_discount(order.total_amount)

        with transaction.atomic():
            order.discount_amount = discount_amount
            order.final_amount = max(
                order.total_amount - discount_amount + order.delivery_cost,
                Decimal('0'),
            )
            order.save(update_fields=['discount_amount', 'final_amount', 'updated_at'])

            promo.uses_count += 1
            promo.save(update_fields=['uses_count'])

        return {
            'discount_amount': discount_amount,
            'new_final_amount': order.final_amount,
        }
