from rest_framework import serializers
from products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class KioskProductSerializer(serializers.ModelSerializer):
    """
    Serializer for products exposed at GET /api/v1/kiosk/products/.

    Fields match the kiosk display requirements:
    id, name, price, barcode, category, image_url, stock_quantity.
    """

    category = CategorySerializer(read_only=True)
    barcode = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    stock_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "price",
            "barcode",
            "category",
            "image_url",
            "stock_quantity",
        )

    def get_barcode(self, obj) -> str | None:
        """Return primary barcode code, or first available barcode."""
        barcodes = list(obj.barcodes.all())
        primary = next((b.code for b in barcodes if b.is_primary), None)
        if primary:
            return primary
        return barcodes[0].code if barcodes else None

    def get_image_url(self, obj) -> str | None:
        """Return URL of the first product image."""
        request = self.context.get("request")
        images = list(obj.images.all())
        if not images:
            return None
        image = images[0].image
        if request:
            return request.build_absolute_uri(image.url)
        return image.url

    def get_stock_quantity(self, obj) -> float | None:
        """Return available stock quantity for the requested store."""
        store = self.context.get("store")
        if store is None:
            return None
        stocks = list(obj.stocks.all())
        stock = next((s for s in stocks if s.store_id == store.id), None)
        if stock is None:
            return None
        # available_quantity = quantity - reserved_quantity (>= 0)
        quantity = stock.quantity - stock.reserved_quantity
        return float(max(quantity, 0))
