from django.urls import path
from . import views

urlpatterns = [
    path("products/", views.KioskProductsView.as_view(), name="kiosk-products"),
    path("products/by-barcode/<str:value>/", views.get_product_by_barcode, name="product-by-barcode"),
]
