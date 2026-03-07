import datetime
import decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from common.models import Address
from stores.models import Store
from products.models import Category, Product, ProductImage, ProductVideo, ProductPrice, Stock


@pytest.mark.django_db
def test_category_clean_prevents_cycles():
    root = Category.objects.create(name="Корневая категория")
    child = Category.objects.create(name="Дочерняя категория", parent=root)

    # создаём цикл: root -> child -> root
    root.parent = child

    with pytest.raises(ValidationError):
        root.clean()


@pytest.mark.django_db
def test_category_str_root_category():
    category = Category.objects.create(name="Овощи")

    assert str(category) == "Овощи"


@pytest.mark.django_db
def test_category_str_nested_categories():
    root = Category.objects.create(name="Продукты")
    sub = Category.objects.create(name="Молочные", parent=root)
    leaf = Category.objects.create(name="Сыры", parent=sub)

    assert str(leaf) == "Продукты / Молочные / Сыры"


@pytest.mark.django_db
def test_product_price_cannot_be_negative():
    category = Category.objects.create(name="Категория для товара")
    product = Product(
        name="Товар с неверной ценой",
        category=category,
        price=decimal.Decimal("-1.00"),
    )

    with pytest.raises(ValidationError):
        product.full_clean()


@pytest.mark.django_db
def test_product_slug_generated_and_unique_for_same_name():
    category = Category.objects.create(name="Категория")

    first = Product.objects.create(
        name="Повторяющийся товар",
        category=category,
        price=decimal.Decimal("10.00"),
    )
    second = Product.objects.create(
        name="Повторяющийся товар",
        category=category,
        price=decimal.Decimal("20.00"),
    )

    assert first.slug
    assert second.slug
    assert first.slug != second.slug


@pytest.mark.django_db
def test_product_image_str_uses_product_name():
    category = Category.objects.create(name="Категория")
    product = Product.objects.create(
        name="Товар с изображением",
        category=category,
        price=decimal.Decimal("5.00"),
    )

    image = ProductImage(product=product)

    assert str(image) == "Изображение товара Товар с изображением"


@pytest.mark.django_db
def test_product_video_str_uses_product_name():
    category = Category.objects.create(name="Категория")
    product = Product.objects.create(
        name="Товар с видео",
        category=category,
        price=decimal.Decimal("15.00"),
    )

    video = ProductVideo(product=product)

    assert str(video) == "Видео товара Товар с видео"


@pytest.mark.django_db
def test_stock_quantity_cannot_be_negative():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин с остатками",
        address=address,
    )
    category = Category.objects.create(name="Категория")
    product = Product.objects.create(
        name="Товар с остатком",
        category=category,
        price=decimal.Decimal("100.00"),
    )

    stock = Stock(
        product=product,
        store=store,
        quantity=-1,
    )

    with pytest.raises(ValidationError):
        stock.full_clean()


@pytest.mark.django_db
def test_stock_unique_constraint_on_product_and_store():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин с остатками",
        address=address,
    )
    category = Category.objects.create(name="Категория")
    product = Product.objects.create(
        name="Товар с остатками",
        category=category,
        price=decimal.Decimal("50.00"),
    )

    Stock.objects.create(
        product=product,
        store=store,
        quantity=10,
    )

    with pytest.raises(IntegrityError):
        Stock.objects.create(
            product=product,
            store=store,
            quantity=20,
        )


@pytest.mark.django_db
def test_stock_str_contains_product_store_and_quantity():
    address = Address.objects.create(
        city="Екатеринбург",
        street="Ленина",
        house="10",
    )
    store = Store.objects.create(
        name="Магазин с остатками",
        address=address,
    )
    category = Category.objects.create(name="Категория")
    product = Product.objects.create(
        name="Товар с остатком",
        category=category,
        price=decimal.Decimal("75.00"),
    )

    stock = Stock(
        product=product,
        store=store,
        quantity=7,
    )

    assert str(stock) == "Товар с остатком в Магазин с остатками: 7"


# --- ProductPrice tests ---

def _make_store(name="Тестовый магазин"):
    address = Address.objects.create(city="Москва", street="Тверская", house="1")
    return Store.objects.create(name=name, address=address)


def _make_product(name="Тестовый товар", price="100.00"):
    category = Category.objects.create(name=f"Кат {name}")
    return Product.objects.create(
        name=name,
        category=category,
        price=decimal.Decimal(price),
    )


@pytest.mark.django_db
def test_product_price_creation():
    store = _make_store()
    product = _make_product()

    pp = ProductPrice.objects.create(
        product=product,
        store=store,
        price=decimal.Decimal("199.99"),
        currency="RUB",
        effective_from=datetime.date(2026, 1, 1),
    )

    assert pp.pk is not None
    assert pp.price == decimal.Decimal("199.99")
    assert pp.currency == "RUB"
    assert pp.is_active is True
    assert pp.effective_to is None


@pytest.mark.django_db
def test_product_price_str():
    store = _make_store()
    product = _make_product()

    pp = ProductPrice(
        product=product,
        store=store,
        price=decimal.Decimal("250.00"),
        currency="RUB",
        effective_from=datetime.date(2026, 3, 1),
    )

    assert "Тестовый товар" in str(pp)
    assert "250.00" in str(pp)
    assert "RUB" in str(pp)


@pytest.mark.django_db
def test_product_price_cannot_be_negative():
    store = _make_store()
    product = _make_product()

    pp = ProductPrice(
        product=product,
        store=store,
        price=decimal.Decimal("-10.00"),
        effective_from=datetime.date(2026, 1, 1),
    )

    with pytest.raises(ValidationError):
        pp.full_clean()


@pytest.mark.django_db
def test_product_price_unique_constraint():
    store = _make_store()
    product = _make_product()
    effective_from = datetime.date(2026, 1, 1)

    ProductPrice.objects.create(
        product=product,
        store=store,
        price=decimal.Decimal("100.00"),
        effective_from=effective_from,
    )

    with pytest.raises(IntegrityError):
        ProductPrice.objects.create(
            product=product,
            store=store,
            price=decimal.Decimal("200.00"),
            effective_from=effective_from,
        )


@pytest.mark.django_db
def test_product_price_with_effective_to():
    store = _make_store()
    product = _make_product()

    pp = ProductPrice.objects.create(
        product=product,
        store=store,
        price=decimal.Decimal("150.00"),
        effective_from=datetime.date(2026, 1, 1),
        effective_to=datetime.date(2026, 12, 31),
    )

    assert pp.effective_to == datetime.date(2026, 12, 31)


@pytest.mark.django_db
def test_product_price_cascade_on_product_delete():
    store = _make_store()
    product = _make_product()

    ProductPrice.objects.create(
        product=product,
        store=store,
        price=decimal.Decimal("99.00"),
        effective_from=datetime.date(2026, 1, 1),
    )

    assert ProductPrice.objects.count() == 1
    product.hard_delete()
    assert ProductPrice.objects.count() == 0


@pytest.mark.django_db
def test_product_price_cascade_on_store_delete():
    store = _make_store()
    product = _make_product()

    ProductPrice.objects.create(
        product=product,
        store=store,
        price=decimal.Decimal("99.00"),
        effective_from=datetime.date(2026, 1, 1),
    )

    assert ProductPrice.objects.count() == 1
    store.hard_delete()
    assert ProductPrice.objects.count() == 0


@pytest.mark.django_db
def test_product_price_default_currency_is_rub():
    store = _make_store()
    product = _make_product()

    pp = ProductPrice.objects.create(
        product=product,
        store=store,
        price=decimal.Decimal("50.00"),
        effective_from=datetime.date(2026, 1, 1),
    )

    assert pp.currency == "RUB"
