from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<uuid:order_id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<uuid:order_id>/items/', views.OrderItemsView.as_view(), name='order-items'),
    path('orders/<uuid:order_id>/items/<uuid:item_id>/', views.OrderItemDetailView.as_view(), name='order-item-detail'),
    path('orders/<uuid:order_id>/submit/', views.OrderSubmitView.as_view(), name='order-submit'),
    path('orders/<uuid:order_id>/cancel/', views.OrderCancelView.as_view(), name='order-cancel'),
]
