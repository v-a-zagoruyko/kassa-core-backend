from rest_framework import serializers
from products.models import Barcode, Product


class BarcodeSerializer(serializers.ModelSerializer):
    """Сериализатор для штрихкодов."""

    class Meta:
        model = Barcode
        fields = ("id", "code", "barcode_type", "is_primary", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_code(self, value):
        """Дополнительная валидация кода на уровне сериализатора."""
        # Проверка уникальности уже в модели, но можно добавить здесь
        instance_pk = self.instance.pk if self.instance else None
        if Barcode.objects.filter(code=value).exclude(pk=instance_pk).exists():
            raise serializers.ValidationError("Штрихкод с этим кодом уже существует.")
        return value


class ProductDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор товара с штрихкодами."""

    barcodes = BarcodeSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "category",
            "price",
            "is_active",
            "barcodes",
            "created_at",
            "updated_at",
        )
