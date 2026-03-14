"""Модели платёжного модуля."""

from django.db import models

from common.models import BaseModel


class PaymentMethod(BaseModel):
    """Метод оплаты (card, sbp, cash и т.д.)."""

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Код",
        help_text="Технический код: card, sbp, cash",
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name="Название",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        db_index=True,
    )

    class Meta:
        verbose_name = "Метод оплаты"
        verbose_name_plural = "Методы оплаты"
        ordering = ["name"]

    def __str__(self):
        return self.display_name


class Payment(BaseModel):
    """Платёж по заказу."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        PROCESSING = "processing", "В обработке"
        COMPLETED = "completed", "Завершён"
        FAILED = "failed", "Ошибка"
        REFUNDED = "refunded", "Возвращён"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Заказ",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма",
    )
    currency = models.CharField(
        max_length=3,
        default="RUB",
        verbose_name="Валюта",
    )
    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Метод оплаты",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
        db_index=True,
    )
    acquiring_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="ID платежа у эквайера",
        db_index=True,
    )
    acquiring_data = models.JSONField(
        default=dict,
        verbose_name="Данные эквайера",
        help_text="Raw response от эквайера",
    )
    initiated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Инициирован в",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Завершён в",
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Отказ в",
    )
    failure_reason = models.TextField(
        blank=True,
        default="",
        verbose_name="Причина отказа",
    )

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-initiated_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["status", "initiated_at"]),
        ]

    def __str__(self):
        return f"Платёж {self.id} — {self.get_status_display()} ({self.amount} {self.currency})"


class PaymentTransaction(BaseModel):
    """Транзакция в рамках платежа (charge, refund, partial_refund)."""

    class TransactionType(models.TextChoices):
        CHARGE = "charge", "Списание"
        REFUND = "refund", "Возврат"
        PARTIAL_REFUND = "partial_refund", "Частичный возврат"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Ошибка"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Платёж",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="Тип транзакции",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
        db_index=True,
    )
    acquiring_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="ID транзакции у эквайера",
    )
    raw_data = models.JSONField(
        default=dict,
        verbose_name="Raw данные",
    )

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Транзакция {self.id} [{self.get_transaction_type_display()}] — {self.get_status_display()}"
