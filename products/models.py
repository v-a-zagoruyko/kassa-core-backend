from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from autoslug import AutoSlugField
import re

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


class Barcode(BaseModel):
    """Штрихкод товара (EAN-13, QR-код, Code-128, Data Matrix)."""

    class BarcodeType(models.TextChoices):
        """Типы штрихкодов."""
        EAN_13 = "ean13", "EAN-13"
        QR = "qr", "QR-код"
        CODE_128 = "code128", "Code-128"
        DATA_MATRIX = "datamatrix", "Data Matrix"

    # Поля модели
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="barcodes",
        verbose_name="Товар",
        help_text="Товар, к которому относится штрихкод",
    )

    code = models.CharField(
        max_length=200,  # Data Matrix может быть длинным
        unique=True,
        verbose_name="Код штрихкода",
        db_index=True,
        help_text="Уникальный код штрихкода (EAN-13, QR, Code-128 или Data Matrix)",
    )

    barcode_type = models.CharField(
        max_length=20,
        choices=BarcodeType.choices,
        default=BarcodeType.EAN_13,
        verbose_name="Тип штрихкода",
        db_index=True,
        help_text="Тип: EAN-13, QR-код, Code-128 или Data Matrix",
    )

    is_primary = models.BooleanField(
        default=False,
        verbose_name="Основной штрихкод",
        db_index=True,
        help_text="Только один основной штрихкод на товар",
    )

    class Meta:
        verbose_name = "Штрихкод"
        verbose_name_plural = "Штрихкоды"
        ordering = ("-is_primary", "barcode_type", "created_at")
        indexes = [
            models.Index(fields=("code",)),
            models.Index(fields=("product_id",)),
            models.Index(fields=("barcode_type",)),
            models.Index(fields=("product_id", "is_primary")),
        ]
        constraints = [
            # Только один основной штрихкод на товар
            models.UniqueConstraint(
                fields=("product_id", "is_primary"),
                condition=models.Q(is_primary=True),
                name="uniq_primary_barcode_per_product",
            ),
        ]

    def clean(self):
        """Валидация формата кода в зависимости от типа."""
        super().clean()

        # EAN-13: ровно 13 цифр
        if self.barcode_type == self.BarcodeType.EAN_13:
            if not re.match(r"^\d{13}$", self.code):
                raise ValidationError(
                    {
                        "code": "EAN-13 должен содержать ровно 13 цифр. "
                        f"Получено: {self.code} ({len(self.code)} символов)."
                    }
                )
            # Проверка контрольной суммы EAN-13
            if not self._validate_ean13_checksum():
                raise ValidationError(
                    {
                        "code": "Неверная контрольная сумма EAN-13. "
                        "Проверьте последнюю цифру кода."
                    }
                )

        # QR-код: строка любой длины, но не пустая
        elif self.barcode_type == self.BarcodeType.QR:
            if not self.code or len(self.code) > 200:
                raise ValidationError(
                    {
                        "code": "QR-код должен быть непустой строкой (макс. 200 символов). "
                        f"Получено: {len(self.code)} символов."
                    }
                )

        # Code-128: буквы, цифры, спецсимволы (не пустая строка, макс 200)
        elif self.barcode_type == self.BarcodeType.CODE_128:
            if not self.code or len(self.code) > 200:
                raise ValidationError(
                    {
                        "code": "Code-128 должен быть непустой строкой (макс. 200 символов). "
                        f"Получено: {len(self.code)} символов."
                    }
                )

        # Data Matrix: строка любой длины (макс 200)
        elif self.barcode_type == self.BarcodeType.DATA_MATRIX:
            if not self.code or len(self.code) > 200:
                raise ValidationError(
                    {
                        "code": "Data Matrix должен быть непустой строкой (макс. 200 символов). "
                        f"Получено: {len(self.code)} символов."
                    }
                )

        # Проверка уникальности кода
        existing = Barcode.objects.filter(code=self.code).exclude(pk=self.pk)
        if existing.exists():
            raise ValidationError(
                {"code": f'Штрихкод "{self.code}" уже используется для другого товара.'}
            )

        # Если это основной штрихкод, проверить, что нет других основных
        if self.is_primary:
            existing_primary = Barcode.objects.filter(
                product_id=self.product_id,
                is_primary=True
            ).exclude(pk=self.pk)
            if existing_primary.exists():
                raise ValidationError(
                    {
                        "is_primary": "У товара уже есть основной штрихкод. "
                        "Удалите флаг основного у другого штрихкода."
                    }
                )

    def save(self, *args, **kwargs):
        """Очистка данных перед сохранением."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        type_label = self.get_barcode_type_display()
        primary_mark = " [основной]" if self.is_primary else ""
        return f"{self.code} ({type_label}){primary_mark}"

    @staticmethod
    def _validate_ean13_checksum(code: str = None) -> bool:
        """Проверка контрольной суммы EAN-13."""
        if not code or len(code) != 13 or not code.isdigit():
            return False

        # Алгоритм проверки контрольной суммы EAN-13:
        # 1. Умножить нечетные позиции (слева направо, 1-индексированные) на 1
        # 2. Умножить четные позиции на 3
        # 3. Суммировать
        # 4. Контрольная цифра = (10 - (сумма % 10)) % 10

        total = 0
        for i, digit in enumerate(code[:-1]):  # Все кроме последней цифры
            multiplier = 1 if i % 2 == 0 else 3
            total += int(digit) * multiplier

        calculated_checksum = (10 - (total % 10)) % 10
        provided_checksum = int(code[-1])

        return calculated_checksum == provided_checksum
