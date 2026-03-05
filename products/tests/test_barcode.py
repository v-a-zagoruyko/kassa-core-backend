import pytest
from django.core.exceptions import ValidationError

from products.models import Barcode, Product, Category


@pytest.mark.django_db
class TestBarcodeModel:
    """Тесты модели Barcode."""

    @pytest.fixture
    def category(self):
        """Создать категорию для тестов."""
        return Category.objects.create(name="Тестовая категория")

    @pytest.fixture
    def product(self, category):
        """Создать товар для тестов."""
        return Product.objects.create(
            name="Товар для тестирования",
            category=category,
            price=100.00,
        )

    # === EAN-13 тесты ===

    def test_create_valid_ean13_barcode(self, product):
        """Создание корректного EAN-13 штрихкода."""
        barcode = Barcode.objects.create(
            product=product,
            code="5901234123457",  # Валидный EAN-13
            barcode_type=Barcode.BarcodeType.EAN_13,
        )
        assert barcode.code == "5901234123457"
        assert barcode.barcode_type == Barcode.BarcodeType.EAN_13
        assert barcode.is_primary is False

    def test_ean13_invalid_length(self, product):
        """EAN-13 с неверной длиной должен вызвать ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            barcode = Barcode(
                product=product,
                code="590123412345",  # 12 символов вместо 13
                barcode_type=Barcode.BarcodeType.EAN_13,
            )
            barcode.full_clean()

        assert "13 цифр" in str(exc_info.value)

    def test_ean13_invalid_checksum(self, product):
        """EAN-13 с неверной контрольной суммой должен вызвать ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            barcode = Barcode(
                product=product,
                code="5901234123458",  # Неверная контрольная сумма
                barcode_type=Barcode.BarcodeType.EAN_13,
            )
            barcode.full_clean()

        assert "контрольная сумма" in str(exc_info.value).lower()

    def test_ean13_non_numeric(self, product):
        """EAN-13 с буквами должен вызвать ValidationError."""
        with pytest.raises(ValidationError):
            barcode = Barcode(
                product=product,
                code="590123412345A",
                barcode_type=Barcode.BarcodeType.EAN_13,
            )
            barcode.full_clean()

    # === QR-код тесты ===

    def test_create_valid_qr_barcode(self, product):
        """Создание корректного QR-кода."""
        barcode = Barcode.objects.create(
            product=product,
            code="https://example.com/product/123",
            barcode_type=Barcode.BarcodeType.QR,
        )
        assert barcode.barcode_type == Barcode.BarcodeType.QR

    def test_qr_empty_code(self, product):
        """QR-код с пустым кодом должен вызвать ValidationError."""
        with pytest.raises(ValidationError):
            barcode = Barcode(
                product=product,
                code="",
                barcode_type=Barcode.BarcodeType.QR,
            )
            barcode.full_clean()

    # === Code-128 тесты ===

    def test_create_valid_code128_barcode(self, product):
        """Создание корректного Code-128 штрихкода."""
        barcode = Barcode.objects.create(
            product=product,
            code="CODE-128-ABC123",
            barcode_type=Barcode.BarcodeType.CODE_128,
        )
        assert barcode.barcode_type == Barcode.BarcodeType.CODE_128

    # === Data Matrix тесты ===

    def test_create_valid_datamatrix_barcode(self, product):
        """Создание корректного Data Matrix кода."""
        barcode = Barcode.objects.create(
            product=product,
            code="01234567890123210321DA",
            barcode_type=Barcode.BarcodeType.DATA_MATRIX,
        )
        assert barcode.barcode_type == Barcode.BarcodeType.DATA_MATRIX

    # === Общие тесты ===

    def test_barcode_unique_code(self, product):
        """Штрихкод с дублирующимся кодом должен вызвать ошибку."""
        Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
        )

        with pytest.raises(ValidationError) as exc_info:
            barcode = Barcode(
                product=product,
                code="5901234123457",
                barcode_type=Barcode.BarcodeType.QR,
            )
            barcode.full_clean()

        assert "уже используется" in str(exc_info.value)

    def test_primary_barcode_unique_per_product(self, product):
        """Только один основной штрихкод на товар."""
        # Создать первый основной
        Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
            is_primary=True,
        )

        # Попытаться создать второй основной
        with pytest.raises(ValidationError) as exc_info:
            barcode = Barcode(
                product=product,
                code="https://example.com",
                barcode_type=Barcode.BarcodeType.QR,
                is_primary=True,
            )
            barcode.full_clean()

        assert "основной" in str(exc_info.value).lower()

    def test_multiple_barcodes_per_product(self, product):
        """Товар может иметь несколько штрихкодов."""
        barcode1 = Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
            is_primary=True,
        )
        barcode2 = Barcode.objects.create(
            product=product,
            code="https://example.com/product",
            barcode_type=Barcode.BarcodeType.QR,
            is_primary=False,
        )

        assert product.barcodes.count() == 2
        assert product.barcodes.filter(is_primary=True).count() == 1

    def test_barcode_string_representation(self, product):
        """Проверка строкового представления."""
        barcode = Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
            is_primary=True,
        )

        assert str(barcode) == "5901234123457 (EAN-13) [основной]"

    def test_barcode_ordering(self, product):
        """Проверка сортировки штрихкодов (основной впереди)."""
        barcode1 = Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
            is_primary=False,
        )
        barcode2 = Barcode.objects.create(
            product=product,
            code="https://example.com",
            barcode_type=Barcode.BarcodeType.QR,
            is_primary=True,
        )

        barcodes = list(product.barcodes.all())
        assert barcodes[0].is_primary is True
        assert barcodes[1].is_primary is False


@pytest.mark.django_db
class TestBarcodeAPI:
    """Тесты API для штрихкодов."""

    @pytest.fixture
    def category(self):
        return Category.objects.create(name="Тестовая категория")

    @pytest.fixture
    def product(self, category):
        return Product.objects.create(
            name="Товар для тестирования",
            category=category,
            price=100.00,
        )

    @pytest.fixture
    def store(self):
        from stores.models import Store
        from common.models import Address
        
        address = Address.objects.create(
            city="Тюмень",
            street="Ленина",
            house="1",
        )
        return Store.objects.create(
            name="Тестовая точка продаж",
            address=address
        )

    @pytest.fixture
    def stock(self, product, store):
        from products.models import Stock
        return Stock.objects.create(
            product=product,
            store=store,
            quantity=10,
        )

    def test_get_product_by_barcode(self, client, product, store, stock):
        """GET /api/v1/kiosk/products/by-barcode/{value}/"""
        barcode = Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
        )

        response = client.get(
            f"/api/v1/kiosk/products/by-barcode/{barcode.code}/",
            {"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product"]["id"] == str(product.id)
        assert data["barcode"]["code"] == barcode.code

    def test_get_product_by_barcode_missing_store_id(self, client, product):
        """GET /api/v1/kiosk/products/by-barcode/ без store_id."""
        barcode = Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
        )

        response = client.get(
            f"/api/v1/kiosk/products/by-barcode/{barcode.code}/"
        )

        assert response.status_code == 400
        data = response.json()
        assert "store_id" in data["error"]["message"]

    def test_get_product_by_barcode_not_found(self, client, store):
        """GET /api/v1/kiosk/products/by-barcode/ с несуществующим кодом."""
        response = client.get(
            f"/api/v1/kiosk/products/by-barcode/NONEXISTENT/",
            {"store_id": str(store.id)},
        )

        assert response.status_code == 404

    def test_get_product_by_barcode_out_of_stock(self, client, product, store):
        """GET /api/v1/kiosk/products/by-barcode/ товара нет в наличии."""
        barcode = Barcode.objects.create(
            product=product,
            code="5901234123457",
            barcode_type=Barcode.BarcodeType.EAN_13,
        )
        from products.models import Stock
        stock = Stock.objects.create(
            product=product,
            store=store,
            quantity=0,
        )

        response = client.get(
            f"/api/v1/kiosk/products/by-barcode/{barcode.code}/",
            {"store_id": str(store.id)},
        )

        assert response.status_code == 422
        data = response.json()
        assert "PRODUCT_OUT_OF_STOCK" in data["error"]["code"]
