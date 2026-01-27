import uuid
from django.db import models
from django.utils import timezone


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата удаления",
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалено",
        db_index=True,
    )

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        abstract = True


class BaseModel(TimestampMixin, SoftDeleteMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.id)


class Address(models.Model):
    city = models.CharField(
        max_length=255,
        verbose_name="Город",
        db_index=True,
    )
    street = models.CharField(
        max_length=255,
        verbose_name="Улица",
        db_index=True,
    )
    house = models.CharField(
        max_length=50,
        verbose_name="Дом",
    )
    apartment = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Квартира/Офис",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Широта",
        help_text="Координата для расчета расстояний",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Долгота",
        help_text="Координата для расчета расстояний",
    )

    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"
        indexes = [
            models.Index(fields=["city", "street"]),
        ]

    def __str__(self):
        parts = [self.city, self.street, self.house]
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)
