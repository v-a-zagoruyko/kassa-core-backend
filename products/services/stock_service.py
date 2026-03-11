"""Stock service — business logic for product availability."""

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def get_available_quantity(product, store) -> Decimal:
    """
    Return available (unreserved) quantity of a product in a given store.

    :param product: Product instance or product_id
    :param store: Store instance or store_id
    :return: Decimal — available quantity (>= 0)
    """
    from products.models import Stock

    try:
        stock = Stock.objects.get(product=product, store=store)
        return stock.available_quantity
    except Stock.DoesNotExist:
        logger.debug(
            "No stock record for product=%s store=%s",
            getattr(product, "id", product),
            getattr(store, "id", store),
        )
        return Decimal("0")
