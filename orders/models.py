from django.db import models
from django.conf import settings
from common.models import BaseModel
from stores.models import Store, Kiosk
from products.models import Product


class Order(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PENDING = 'pending', 'Ожидает обработки'
        PENDING_PAYMENT = 'pending_payment', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        COMPLETED = 'completed', 'Завершён'
        CANCELLED = 'cancelled', 'Отменён'

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Наличные'
        CARD = 'card', 'Банковская карта'
        QR = 'qr', 'QR-код'

    class OrderType(models.TextChoices):
        DELIVERY = 'delivery', 'Доставка'
        PICKUP = 'pickup', 'Самовывоз'
        KIOSK = 'kiosk', 'Касса'

    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        ASSIGNED = 'assigned', 'Курьер назначен'
        IN_TRANSIT = 'in_transit', 'В пути'
        DELIVERED = 'delivered', 'Доставлен'
        FAILED = 'failed', 'Не удалось доставить'

    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Точка продаж',
    )
    kiosk = models.ForeignKey(
        Kiosk,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Касса',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Покупатель',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус',
    )
    order_type = models.CharField(
        max_length=10,
        choices=OrderType.choices,
        default=OrderType.DELIVERY,
        verbose_name='Тип заказа',
    )
    delivery_address = models.ForeignKey(
        'common.Address',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Адрес доставки',
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        null=True,
        blank=True,
        verbose_name='Статус доставки',
    )
    estimated_delivery_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ожидаемое время доставки',
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Фактическое время доставки',
    )
    delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Стоимость доставки',
    )
    courier_comment = models.TextField(
        blank=True,
        default='',
        verbose_name='Комментарий к заказу',
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Сумма',
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Скидка',
    )
    final_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Итоговая сумма',
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        null=True,
        blank=True,
        verbose_name='Способ оплаты',
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Завершён в',
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['store', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_type', 'status']),
        ]

    def __str__(self):
        return f'Заказ {self.id} — {self.get_status_display()}'


class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='Товар',
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество',
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Цена',
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Сумма',
    )
    marking_code = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Код маркировки',
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'


class OrderStatus(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='Заказ',
    )
    status = models.CharField(
        max_length=20,
        choices=Order.Status.choices,
        verbose_name='Статус',
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Изменил',
    )
    comment = models.TextField(
        blank=True,
        default='',
        verbose_name='Комментарий',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата',
    )

    class Meta:
        verbose_name = 'История статусов заказа'
        verbose_name_plural = 'История статусов заказов'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.order} → {self.get_status_display()}'


class Reservation(BaseModel):
    """Резервирование товара для заказа."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активен'
        COMPLETED = 'completed', 'Выполнен'
        EXPIRED = 'expired', 'Истёк'
        RELEASED = 'released', 'Освобождён'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='Товар',
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='Магазин',
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name='Количество',
    )
    expires_at = models.DateTimeField(
        verbose_name='Истекает в',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Статус',
        db_index=True,
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Освобождён в',
    )

    class Meta:
        verbose_name = 'Резервирование'
        verbose_name_plural = 'Резервирования'
        indexes = [
            models.Index(fields=['product', 'store']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def is_expired(self) -> bool:
        """Check if the reservation has expired."""
        from django.utils import timezone
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f'Резерв {self.product} x{self.quantity} для {self.order}'


class OrderStatusLog(models.Model):
    """Log entry for order status changes (used for delivery tracking)."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_logs',
        verbose_name='Заказ',
    )
    status = models.CharField(
        max_length=20,
        choices=Order.Status.choices,
        verbose_name='Статус',
    )
    comment = models.TextField(
        blank=True,
        default='',
        verbose_name='Комментарий',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата',
    )

    class Meta:
        verbose_name = 'Лог статуса заказа'
        verbose_name_plural = 'Логи статусов заказов'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.order} → {self.get_status_display()} @ {self.created_at}'


class Package(BaseModel):
    """Упаковка (пакет, сумка) для заказа."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='packages',
        verbose_name='Заказ',
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена',
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество',
    )

    class Meta:
        verbose_name = 'Упаковка'
        verbose_name_plural = 'Упаковки'

    def __str__(self):
        return f'{self.name} x{self.quantity} для {self.order_id}'


class PromoCode(BaseModel):
    """Промокод для скидки на заказ."""

    class DiscountType(models.TextChoices):
        PERCENT = 'percent', 'Процент'
        FIXED = 'fixed', 'Фиксированная сумма'

    class OrderTypes(models.TextChoices):
        ALL = 'all', 'Все типы'
        DELIVERY = 'delivery', 'Доставка'
        PICKUP = 'pickup', 'Самовывоз'

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Код промокода',
        db_index=True,
    )
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        verbose_name='Тип скидки',
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Размер скидки',
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Минимальная сумма заказа',
    )
    valid_from = models.DateTimeField(
        verbose_name='Действует с',
    )
    valid_until = models.DateTimeField(
        verbose_name='Действует до',
    )
    max_uses = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Максимальное количество использований',
    )
    uses_count = models.IntegerField(
        default=0,
        verbose_name='Количество использований',
    )
    order_types = models.CharField(
        max_length=10,
        choices=OrderTypes.choices,
        default=OrderTypes.ALL,
        verbose_name='Типы заказов',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        db_index=True,
    )

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'

    def __str__(self):
        return f'{self.code} ({self.get_discount_type_display()}: {self.discount_value})'

    def is_valid(self, order_amount: 'Decimal', order_type: str) -> tuple:
        """Validate the promo code for a given order.

        Returns:
            tuple(bool, str): (is_valid, error_message_or_empty)
        """
        from django.utils import timezone
        from decimal import Decimal

        now = timezone.now()

        if not self.is_active:
            return False, 'Промокод неактивен.'

        if now < self.valid_from:
            return False, 'Промокод ещё не действует.'

        if now > self.valid_until:
            return False, 'Срок действия промокода истёк.'

        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False, 'Лимит использований промокода исчерпан.'

        if order_amount < self.min_order_amount:
            return False, (
                f'Минимальная сумма заказа для этого промокода: {self.min_order_amount} руб.'
            )

        if self.order_types != self.OrderTypes.ALL and self.order_types != order_type:
            return False, f'Промокод действует только для типа "{self.get_order_types_display()}".'

        return True, ''

    def calculate_discount(self, order_amount: 'Decimal') -> 'Decimal':
        """Calculate discount amount for the given order amount."""
        from decimal import Decimal, ROUND_HALF_UP

        if self.discount_type == self.DiscountType.PERCENT:
            discount = order_amount * self.discount_value / Decimal('100')
        else:
            discount = self.discount_value

        result = min(discount, order_amount)
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
