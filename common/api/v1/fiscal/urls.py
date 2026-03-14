"""URL-маршруты фискального API."""

from django.urls import path

from .views import (
    AdminReceiptDetailView,
    AdminReceiptGenerateView,
    AdminReceiptListView,
    AdminReceiptSendView,
    OFDWebhookView,
)

urlpatterns = [
    # Webhook от ОФД
    path('integrations/ofd/webhook/', OFDWebhookView.as_view(), name='ofd-webhook'),

    # Admin API
    path('admin/fiscal/receipts/', AdminReceiptListView.as_view(), name='admin-receipt-list'),
    path('admin/fiscal/receipts/<uuid:receipt_id>/', AdminReceiptDetailView.as_view(), name='admin-receipt-detail'),
    path('admin/fiscal/receipts/<uuid:order_id>/generate/', AdminReceiptGenerateView.as_view(), name='admin-receipt-generate'),
    path('admin/fiscal/receipts/<uuid:receipt_id>/send/', AdminReceiptSendView.as_view(), name='admin-receipt-send'),
]
