"""Модели фискального домена (чеки и ОФД по 54-ФЗ)."""

import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from common.models import BaseModel


class Receipt(BaseModel):
    """Фискальный чек по 54-ФЗ."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает отправки'
        SENT = 'sent', 'Отправлен'
        CONFIRMED = 'confirmed', 'Подтверждён'
        FAILED = 'failed', 'Ошибка'

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='receipt',
        verbose_name='Заказ',
    )
    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name='Номер чека',
    )
    fiscal_data = models.JSONField(
        verbose_name='Фискальные данные',
        help_text='Данные чека по 54-ФЗ',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус',
        db_index=True,
    )
    ofd_response = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Последний ответ ОФД',
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Отправлен в',
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Подтверждён в',
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='Сообщение об ошибке',
    )

    class Meta:
        verbose_name = 'Чек'
        verbose_name_plural = 'Чеки'
        indexes = [
            models.Index(fields=['status', 'sent_at']),
        ]

    def __str__(self):
        return f'Чек {self.receipt_number} ({self.get_status_display()})'


class ReceiptItem(models.Model):
    """Позиция фискального чека."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
    )
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Чек',
    )
    product_name = models.CharField(
        max_length=255,
        verbose_name='Наименование товара',
        help_text='Название товара на момент продажи',
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена за единицу',
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Итого по позиции',
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        verbose_name='Ставка НДС, %',
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма НДС',
    )

    class Meta:
        verbose_name = 'Позиция чека'
        verbose_name_plural = 'Позиции чека'

    def save(self, *args, **kwargs):
        """Автоматически рассчитывает total и tax_amount перед сохранением."""
        self.total = (self.price * self.quantity).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        # НДС исчисляется «изнутри»: tax = total * rate / (100 + rate)
        tax_divisor = Decimal('100') + self.tax_rate
        self.tax_amount = (self.total * self.tax_rate / tax_divisor).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product_name} x{self.quantity}'


class ReceiptStatus(models.Model):
    """История смен статусов чека."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
    )
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='Чек',
    )
    status = models.CharField(
        max_length=20,
        choices=Receipt.Status.choices,
        verbose_name='Статус',
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата изменения',
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name='Комментарий',
    )

    class Meta:
        verbose_name = 'История статуса чека'
        verbose_name_plural = 'История статусов чеков'
        ordering = ['changed_at']

    def __str__(self):
        return f'{self.receipt} → {self.get_status_display()}'


class ReturnReceipt(BaseModel):
    """Чек возврата прихода по 54-ФЗ (признак расчёта = 2)."""

    return_obj = models.OneToOneField(
        'returns.Return',
        on_delete=models.PROTECT,
        related_name='receipt',
        verbose_name='Возврат',
    )
    original_receipt = models.ForeignKey(
        Receipt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_receipts',
        verbose_name='Исходный чек продажи',
    )
    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name='Номер чека',
    )
    fiscal_data = models.JSONField(verbose_name='Фискальные данные (54-ФЗ)')
    status = models.CharField(
        max_length=20,
        choices=Receipt.Status.choices,
        default=Receipt.Status.PENDING,
        db_index=True,
        verbose_name='Статус',
    )
    ofd_response = models.JSONField(null=True, blank=True, verbose_name='Последний ответ ОФД')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Отправлен в')
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='Подтверждён в')
    error_message = models.TextField(null=True, blank=True, verbose_name='Сообщение об ошибке')

    class Meta:
        verbose_name = 'Чек возврата'
        verbose_name_plural = 'Чеки возвратов'
        indexes = [models.Index(fields=['status', 'sent_at'])]

    def __str__(self):
        return f'Чек возврата {self.receipt_number} ({self.get_status_display()})'


class ReturnReceiptItem(models.Model):
    """Позиция чека возврата."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        ReturnReceipt,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Чек возврата',
    )
    product_name = models.CharField(max_length=255, verbose_name='Наименование')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за единицу')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Итого')
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        verbose_name='Ставка НДС, %',
    )
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма НДС')

    class Meta:
        verbose_name = 'Позиция чека возврата'
        verbose_name_plural = 'Позиции чека возврата'

    def save(self, *args, **kwargs):
        self.total = (self.price * self.quantity).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        tax_divisor = Decimal('100') + self.tax_rate
        self.tax_amount = (self.total * self.tax_rate / tax_divisor).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product_name} x{self.quantity}'


class OFDResponse(models.Model):
    """История запросов к ОФД."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID',
    )
    receipt = models.ForeignKey(
        Receipt,
        on_delete=models.CASCADE,
        related_name='ofd_responses',
        verbose_name='Чек',
    )
    response_data = models.JSONField(
        verbose_name='Данные ответа',
    )
    status_code = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='HTTP статус код',
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='Сообщение об ошибке',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )

    class Meta:
        verbose_name = 'Ответ ОФД'
        verbose_name_plural = 'Ответы ОФД'
        ordering = ['-created_at']

    def __str__(self):
        return f'Ответ ОФД для {self.receipt} ({self.created_at})'
