from django.urls import path

from . import views

urlpatterns = [
    path("payments/methods/", views.PaymentMethodListView.as_view(), name="payment-methods-list"),
    path("payments/<uuid:payment_id>/", views.PaymentDetailView.as_view(), name="payment-detail"),
    path("orders/<uuid:order_id>/pay/", views.OrderPayView.as_view(), name="order-pay"),
]
