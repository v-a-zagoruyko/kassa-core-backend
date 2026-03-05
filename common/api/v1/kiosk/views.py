from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from products.models import Barcode, Product, Stock


@api_view(["GET"])
def get_product_by_barcode(request, value):
    """
    GET /api/v1/kiosk/products/by-barcode/{value}/

    Получить товар по штрихкоду.

    Query параметры:
    - store_id (required) - ID точки продаж

    Response:
    {
        "product": {...},
        "barcode": {...},
        "stock": {...}
    }
    """
    store_id = request.query_params.get("store_id")
    if not store_id:
        return Response(
            {
                "error": {
                    "code": "MISSING_STORE_ID",
                    "message": 'Параметр "store_id" обязателен.',
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Найти штрихкод по коду
    barcode = get_object_or_404(Barcode, code=value)
    product = barcode.product

    # Проверить доступность товара
    try:
        stock = Stock.objects.get(product=product, store_id=store_id)
    except Stock.DoesNotExist:
        return Response(
            {
                "error": {
                    "code": "PRODUCT_NOT_AVAILABLE",
                    "message": f"Товар '{product.name}' недоступен в этой точке продаж.",
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if not product.is_active or stock.quantity <= 0:
        return Response(
            {
                "error": {
                    "code": "PRODUCT_OUT_OF_STOCK",
                    "message": f"Товар '{product.name}' недоступен (отсутствует в наличии).",
                }
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Составить response
    return Response(
        {
            "product": {
                "id": str(product.id),
                "name": product.name,
                "price": str(product.price),
                "description": product.description,
            },
            "barcode": {
                "code": barcode.code,
                "type": barcode.barcode_type,
                "is_primary": barcode.is_primary,
            },
            "stock": {
                "quantity": stock.quantity,
                "available": stock.quantity > 0,
            },
        },
        status=status.HTTP_200_OK,
    )
