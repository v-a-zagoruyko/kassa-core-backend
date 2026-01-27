from django.db import models
from django.utils.text import slugify
from common.models import BaseModel, Address


class Store(BaseModel):
    name = models.CharField(
        max_length=255,
        verbose_name="Название",
    )
    code = models.SlugField(
        max_length=255,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Код",
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
    )

    class Meta:
        verbose_name = "Точка продаж"
        verbose_name_plural = "Точки продаж"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.code = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StoreWorkingHours(models.Model):
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

    def __str__(self):
        return f"{self.store.name} - {self.get_day_of_week_display()}"


class StoreSpecialHours(models.Model):
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

    def __str__(self):
        return f"{self.store.name} - {self.date}"
