from django.urls import path
from . import views

urlpatterns = [
    path("products/by-barcode/<str:value>/", views.get_product_by_barcode, name="product-by-barcode"),
]
