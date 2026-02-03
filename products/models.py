from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from autoslug import AutoSlugField

from common.models import BaseModel


class Category(BaseModel):
    """Категория товаров (иерархическая)."""

    name = models.CharField(
        max_length=255,
        verbose_name="Название",
    )
    slug = AutoSlugField(
        max_length=255,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Код (slug)",
        populate_from="name",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
        verbose_name="Родительская категория",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки",
        db_index=True,
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
        db_index=True,
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ("parent__sort_order", "sort_order", "name")

    def clean(self) -> None:
        super().clean()
        parent = self.parent
        while parent is not None:
            if parent == self:
                raise ValidationError(
                    {"parent": "Нельзя выбрать родительскую категорию, приводящую к циклу."}
                )
            parent = parent.parent

    def __str__(self):
        path = []
        parent = self.parent
        while parent is not None:
            path.append(parent.name)
            parent = parent.parent
        path.reverse()
        if path:
            return " / ".join(path) + " / " + self.name
        return self.name


class Product(BaseModel):
    """Товар в каталоге."""

    name = models.CharField(
        max_length=255,
        verbose_name="Название",
    )
    slug = AutoSlugField(
        max_length=255,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Код (slug)",
        populate_from="name",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Категория",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание",
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Цена",
        validators=[
            MinValueValidator(0, message="Цена не может быть отрицательной."),
        ],
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        db_index=True,
    )

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ("name",)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """Изображение товара."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Товар",
    )
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        verbose_name="Изображение",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок",
        db_index=True,
    )

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"Изображение товара {self.product.name}"


class ProductVideo(models.Model):
    """Видео о товаре."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="videos",
        verbose_name="Товар",
    )
    file = models.FileField(
        upload_to="product_videos/%Y/%m/",
        verbose_name="Файл видео",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок",
        db_index=True,
    )

    class Meta:
        verbose_name = "Видео товара"
        verbose_name_plural = "Видео товаров"
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"Видео товара {self.product.name}"


class Stock(BaseModel):
    """Остатки товара по точкам продаж."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stocks",
        verbose_name="Товар",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="stocks",
        verbose_name="Точка продаж",
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество на складе",
        validators=[
            MinValueValidator(0, message="Количество не может быть отрицательным."),
        ],
    )

    class Meta:
        verbose_name = "Остаток товара"
        verbose_name_plural = "Остатки товаров"
        constraints = [
            models.UniqueConstraint(
                fields=("product", "store"),
                name="uniq_product_store_stock",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} в {self.store}: {self.quantity}"
