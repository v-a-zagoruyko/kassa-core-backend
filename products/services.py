"""
ProductService — cached product data access layer.

Uses Redis cache (via common.cache helpers) with graceful degradation:
if Redis is unavailable, falls back to direct DB queries without caching.

Default TTL: 5 minutes (300 seconds).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

PRODUCT_CACHE_TTL = 300  # 5 minutes


def _make_product_key(product_id) -> str:
    return f"product:{product_id}"


def _make_kiosk_products_key(kiosk_id) -> str:
    return f"kiosk:{kiosk_id}:products"


class ProductService:
    """
    Service for fetching and caching product data.

    Example usage:
        service = ProductService()
        product = service.get_product(product_id)
        products = service.get_products_for_kiosk(kiosk_id)
        service.invalidate_cache(product_id)
    """

    def __init__(self, ttl: int = PRODUCT_CACHE_TTL):
        self.ttl = ttl
        self._cache_available = self._check_cache_available()

    def _check_cache_available(self) -> bool:
        """Check if cache backend is available."""
        try:
            from django.core.cache import cache
            cache.get("__health_check__")
            return True
        except Exception as exc:
            logger.warning("Cache unavailable, running without cache: %s", exc)
            return False

    def _cache_get(self, key: str):
        if not self._cache_available:
            return None
        try:
            from common.cache import cache_get
            return cache_get(key)
        except Exception as exc:
            logger.warning("Cache get error for key %s: %s", key, exc)
            return None

    def _cache_set(self, key: str, value) -> None:
        if not self._cache_available:
            return
        try:
            from common.cache import cache_set
            cache_set(key, value, timeout=self.ttl)
        except Exception as exc:
            logger.warning("Cache set error for key %s: %s", key, exc)

    def _cache_delete(self, key: str) -> None:
        if not self._cache_available:
            return
        try:
            from common.cache import cache_delete
            cache_delete(key)
        except Exception as exc:
            logger.warning("Cache delete error for key %s: %s", key, exc)

    def get_product(self, product_id) -> Optional[dict]:
        """
        Get a single product by ID.

        Returns a dict with product data, or None if not found.
        Caches result for self.ttl seconds.
        """
        from products.models import Product

        cache_key = _make_product_key(product_id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.debug("Cache hit: product %s", product_id)
            return cached

        try:
            product = (
                Product.objects.select_related("category")
                .prefetch_related("barcodes", "images")
                .get(id=product_id, is_active=True)
            )
        except Product.DoesNotExist:
            return None

        data = self._serialize_product(product)
        self._cache_set(cache_key, data)
        logger.debug("Cache miss: product %s — fetched from DB", product_id)
        return data

    def get_products_for_kiosk(self, kiosk_id) -> list:
        """
        Get all active products available for a given kiosk.

        Resolves store from Kiosk, then returns products that have a
        Stock record for that store.
        Caches result for self.ttl seconds.
        """
        from stores.models import Kiosk
        from products.models import Product, Stock

        cache_key = _make_kiosk_products_key(kiosk_id)
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.debug("Cache hit: kiosk %s products", kiosk_id)
            return cached

        try:
            kiosk = Kiosk.objects.select_related("store").get(id=kiosk_id, is_active=True)
        except Kiosk.DoesNotExist:
            logger.debug("Kiosk %s not found or inactive", kiosk_id)
            return []

        store = kiosk.store

        # Products that have stock at this store (quantity > 0)
        product_ids = Stock.objects.filter(
            store=store,
            quantity__gt=0,
        ).values_list("product_id", flat=True)

        products = (
            Product.objects.filter(id__in=product_ids, is_active=True)
            .select_related("category")
            .prefetch_related("barcodes", "images", "stocks")
            .order_by("name")
        )

        data = []
        for product in products:
            product_data = self._serialize_product(product, store=store)
            data.append(product_data)

        self._cache_set(cache_key, data)
        logger.debug(
            "Cache miss: kiosk %s products — fetched %d from DB", kiosk_id, len(data)
        )
        return data

    def invalidate_cache(self, product_id) -> None:
        """
        Invalidate cache for a specific product.

        Deletes the product-level cache key.
        Kiosk-level caches are NOT invalidated here (TTL-based expiry).
        Call invalidate_kiosk_cache(kiosk_id) for kiosk-level invalidation.
        """
        cache_key = _make_product_key(product_id)
        self._cache_delete(cache_key)
        logger.debug("Cache invalidated: product %s", product_id)

    def invalidate_kiosk_cache(self, kiosk_id) -> None:
        """Invalidate cache for a specific kiosk's product list."""
        cache_key = _make_kiosk_products_key(kiosk_id)
        self._cache_delete(cache_key)
        logger.debug("Cache invalidated: kiosk %s products", kiosk_id)

    @staticmethod
    def _serialize_product(product, store=None) -> dict:
        """Convert a Product ORM instance to a serializable dict."""
        # Primary barcode
        primary_barcode = next(
            (b.code for b in product.barcodes.all() if b.is_primary),
            None,
        )

        # Primary image URL
        images = list(product.images.all())
        image_url = images[0].image.url if images else None

        # Stock quantity for the given store
        stock_quantity = None
        if store is not None:
            try:
                stock = next(
                    (s for s in product.stocks.all() if s.store_id == store.id),
                    None,
                )
                if stock is not None:
                    stock_quantity = float(stock.available_quantity)
            except Exception:
                pass

        return {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
            "price": str(product.price),
            "description": product.description,
            "barcode": primary_barcode,
            "category": {
                "id": str(product.category_id),
                "name": product.category.name,
                "slug": product.category.slug,
            },
            "image_url": image_url,
            "stock_quantity": stock_quantity,
            "is_active": product.is_active,
        }
