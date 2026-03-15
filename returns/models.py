from django.conf import settings
from django.db import models

from common.models import BaseModel


class ReturnReason(BaseModel):
    """Справочник причин возврата."""

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Код',
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название',
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='Описание',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна',
        db_index=True,
    )

    class Meta:
        verbose_name = 'Причина возврата'
        verbose_name_plural = 'Причины возврата'

    def __str__(self):
        return f'{self.code} — {self.name}'


class Return(BaseModel):
    """Возврат заказа."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PROCESSING = 'processing', 'В обработке'
        COMPLETED = 'completed', 'Завершён'
        CANCELLED = 'cancelled', 'Отменён'

    class RefundMethod(models.TextChoices):
        CASH = 'cash', 'Наличные'
        CARD = 'card', 'Банковская карта'

    class RefundStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        COMPLETED = 'completed', 'Выполнен'
        FAILED = 'failed', 'Ошибка'

    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name='Заказ',
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_returns',
        verbose_name='Обработал',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус',
        db_index=True,
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Итоговая сумма возврата',
    )
    refund_method = models.CharField(
        max_length=10,
        choices=RefundMethod.choices,
        verbose_name='Способ возврата',
    )
    refund_status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        verbose_name='Статус возврата средств',
    )
    reason = models.ForeignKey(
        ReturnReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returns',
        verbose_name='Причина',
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name='Комментарий',
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Завершён в',
    )

    class Meta:
        verbose_name = 'Возврат'
        verbose_name_plural = 'Возвраты'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['order', 'created_at']),
        ]

    def __str__(self):
        return f'Возврат {self.id} для заказа {self.order_id}'


class ReturnItem(BaseModel):
    """Позиция возврата."""

    return_obj = models.ForeignKey(
        Return,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Возврат',
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.PROTECT,
        related_name='return_items',
        verbose_name='Позиция заказа',
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
    )
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма возврата',
    )

    class Meta:
        verbose_name = 'Позиция возврата'
        verbose_name_plural = 'Позиции возврата'

    def __str__(self):
        return f'Позиция {self.order_item_id} x{self.quantity}'


class ReturnStatus(models.Model):
    """История статусов возврата."""

    return_obj = models.ForeignKey(
        Return,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='Возврат',
    )
    status = models.CharField(
        max_length=20,
        verbose_name='Статус',
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Изменён в',
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_status_changes',
        verbose_name='Изменил',
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name='Комментарий',
    )

    class Meta:
        verbose_name = 'История статусов возврата'
        verbose_name_plural = 'История статусов возвратов'
        ordering = ['changed_at']

    def __str__(self):
        return f'{self.return_obj_id} → {self.status} @ {self.changed_at}'
