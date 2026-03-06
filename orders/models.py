from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.models import BaseModel
from products.models import Product
from stores.models import Store


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    CONFIRMED = "confirmed", "Подтверждён"
    PAID = "paid", "Оплачен"
    IN_PROGRESS = "in_progress", "В процессе"
    READY = "ready", "Готов"
    COMPLETED = "completed", "Завершён"
    CANCELLED = "cancelled", "Отменён"


class Order(BaseModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Точка продаж",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Пользователь",
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
        verbose_name="Статус",
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Итоговая сумма",
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий",
    )

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"Заказ {self.id} [{self.status}]"


class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Товар",
    )
    quantity = models.PositiveIntegerField(
        verbose_name="Количество",
        validators=[MinValueValidator(1, message="Количество должно быть не менее 1.")],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена",
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_order_product",
            ),
        ]

    @property
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
