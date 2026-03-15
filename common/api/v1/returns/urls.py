from django.urls import path

from .views import AdminReturnDetailView, AdminReturnListView, AdminReturnProcessView

urlpatterns = [
    path('admin/returns/', AdminReturnListView.as_view(), name='admin-return-list'),
    path('admin/returns/<uuid:return_id>/', AdminReturnDetailView.as_view(), name='admin-return-detail'),
    path('admin/returns/<uuid:return_id>/process/', AdminReturnProcessView.as_view(), name='admin-return-process'),
]
