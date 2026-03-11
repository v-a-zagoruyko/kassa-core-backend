import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from products.models import Barcode, Product, Stock
from products.services import ProductService
from stores.models import Kiosk

from .serializers import KioskProductSerializer

logger = logging.getLogger(__name__)


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


class KioskProductsPagination(PageNumberPagination):
    """Pagination for kiosk product list: 50 items per page."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class KioskProductsView(APIView):
    """
    GET /api/v1/kiosk/products/

    List products available for a specific kiosk.

    Query parameters:
    - kiosk_id (required) — UUID of the Kiosk
    - category (optional) — filter by category slug
    - search (optional) — full-text search by name/barcode

    Authentication: JWT Bearer token (required).

    Response is paginated (page_size=50).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        kiosk_id = request.query_params.get("kiosk_id")
        if not kiosk_id:
            return Response(
                {
                    "error": {
                        "code": "MISSING_KIOSK_ID",
                        "message": 'Параметр "kiosk_id" обязателен.',
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate kiosk exists
        try:
            kiosk = Kiosk.objects.select_related("store").get(id=kiosk_id, is_active=True)
        except (Kiosk.DoesNotExist, ValueError):
            return Response(
                {
                    "error": {
                        "code": "KIOSK_NOT_FOUND",
                        "message": f"Касса с id={kiosk_id!r} не найдена или неактивна.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        store = kiosk.store

        # Get products that have stock at this store
        stock_product_ids = Stock.objects.filter(
            store=store,
            quantity__gt=0,
        ).values_list("product_id", flat=True)

        queryset = (
            Product.objects.filter(id__in=stock_product_ids, is_active=True)
            .select_related("category")
            .prefetch_related("barcodes", "images", "stocks")
            .order_by("name")
        )

        # Optional: category filter
        category_slug = request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Optional: search filter (name or barcode)
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(barcodes__code__icontains=search)
            ).distinct()

        # Pagination
        paginator = KioskProductsPagination()
        page = paginator.paginate_queryset(queryset, request)

        serializer = KioskProductSerializer(
            page,
            many=True,
            context={"request": request, "store": store},
        )

        return paginator.get_paginated_response(serializer.data)
