from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from autoslug import AutoSlugField

from common.models import Address, BaseModel, UniqueConstraintCheckMixin


class Store(BaseModel):
    name = models.CharField(
        max_length=255,
        verbose_name="Название",
    )
    code = AutoSlugField(
        max_length=255,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Код",
        populate_from="name",
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        related_name="stores",
        verbose_name="Адрес",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
    )
    delivery_radius_km = models.FloatField(
        default=3.0,
        verbose_name="Радиус доставки",
        help_text="Указывается в километрах",
        validators=[
            MinValueValidator(0.01, message="Радиус доставки должен быть больше 0"),
        ],
    )

    class Meta:
        verbose_name = "Точка продаж"
        verbose_name_plural = "Точки продаж"

    def clean(self) -> None:
        super().clean()
        if self.delivery_radius_km is not None and self.delivery_radius_km < 0.01:
            raise ValidationError(
                {"delivery_radius_km": "Радиус доставки должен быть больше 0"}
            )

    def __str__(self):
        return self.name


class StoreWorkingHours(UniqueConstraintCheckMixin, models.Model):
    DAYS_OF_WEEK = [
        (0, "Понедельник"),
        (1, "Вторник"),
        (2, "Среда"),
        (3, "Четверг"),
        (4, "Пятница"),
        (5, "Суббота"),
        (6, "Воскресенье"),
    ]

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="working_hours",
        verbose_name="Точка продаж",
    )
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK,
        verbose_name="День недели",
    )
    open_time = models.TimeField(
        verbose_name="Время открытия",
    )
    close_time = models.TimeField(
        verbose_name="Время закрытия",
    )

    class Meta:
        verbose_name = "Рабочие часы точки продаж"
        verbose_name_plural = "Рабочие часы точек продаж"
        ordering = ("day_of_week",)
        constraints = [
            models.UniqueConstraint(
                fields=("store", "day_of_week"),
                name="uniq_store_day_of_week",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.open_time >= self.close_time:
            raise ValidationError(
                {"close_time": "Время закрытия должно быть позже времени открытия."}
            )

    def save(self, *args, **kwargs):
        self._check_unique_constraint(
            ("store", "day_of_week"),
            "StoreWorkingHours with this store and day_of_week already exists.",
        )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.store.name} - {self.get_day_of_week_display()}"


class StoreSpecialHours(UniqueConstraintCheckMixin, models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="special_hours",
        verbose_name="Точка продаж",
    )
    date = models.DateField(
        verbose_name="Дата",
    )
    open_time = models.TimeField(
        verbose_name="Время открытия",
    )
    close_time = models.TimeField(
        verbose_name="Время закрытия",
    )

    class Meta:
        verbose_name = "Специальные часы точки продаж"
        verbose_name_plural = "Специальные часы точек продаж"
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(
                fields=("store", "date"),
                name="uniq_store_date",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.open_time >= self.close_time:
            raise ValidationError(
                {"close_time": "Время закрытия должно быть позже времени открытия."}
            )

    def save(self, *args, **kwargs):
        self._check_unique_constraint(
            ("store", "date"),
            "StoreSpecialHours with this store and date already exists.",
        )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.store.name} - {self.date}"
