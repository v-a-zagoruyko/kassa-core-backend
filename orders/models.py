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
