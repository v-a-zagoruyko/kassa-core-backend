from django.urls import path
from . import views

urlpatterns = [
    path('stores/<uuid:store_id>/delivery-zones/', views.StoreDeliveryZonesView.as_view(), name='store-delivery-zones'),
    path('delivery/check/', views.DeliveryCheckView.as_view(), name='delivery-check'),
]
