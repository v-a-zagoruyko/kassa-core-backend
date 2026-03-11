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
    lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Широта",
        help_text="Координата магазина (широта)",
    )
    lon = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Долгота",
        help_text="Координата магазина (долгота)",
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


class Kiosk(BaseModel):
    kiosk_number = models.CharField(max_length=50, verbose_name="Номер кассы")
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="kiosks",
        verbose_name="Точка продаж",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Касса"
        verbose_name_plural = "Кассы"
        constraints = [
            models.UniqueConstraint(
                fields=("store", "kiosk_number"),
                name="uniq_store_kiosk_number",
            )
        ]

    def __str__(self):
        return f"{self.store.name} — касса {self.kiosk_number}"


class StoreSettings(BaseModel):
    store = models.OneToOneField(
        Store,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name="Точка продаж",
    )
    receipt_header = models.TextField(blank=True, default="", verbose_name="Заголовок чека")
    receipt_footer = models.TextField(blank=True, default="", verbose_name="Подвал чека")
    allow_cash = models.BooleanField(default=True, verbose_name="Разрешить наличные")
    allow_card = models.BooleanField(default=True, verbose_name="Разрешить карту")
    max_idle_seconds = models.PositiveIntegerField(
        default=120,
        verbose_name="Таймаут бездействия (сек)",
    )

    class Meta:
        verbose_name = "Настройки точки продаж"
        verbose_name_plural = "Настройки точек продаж"

    def __str__(self):
        return f"Настройки: {self.store.name}"


class DeliveryZone(BaseModel):
    """Зона доставки магазина с условиями."""

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="delivery_zones",
        verbose_name="Магазин",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название зоны",
    )
    radius_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Радиус зоны (км)",
        help_text="Максимальное расстояние от магазина для данной зоны",
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Минимальная сумма заказа",
    )
    delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Стоимость доставки",
    )
    delivery_time_minutes = models.IntegerField(
        verbose_name="Время доставки (минут)",
        help_text="ETA в минутах",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
        db_index=True,
    )

    class Meta:
        verbose_name = "Зона доставки"
        verbose_name_plural = "Зоны доставки"
        ordering = ("radius_km",)
        indexes = [
            models.Index(fields=("store", "is_active")),
        ]

    def __str__(self):
        return f"{self.store.name} — {self.name}"
