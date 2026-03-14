from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.api_version, name="api-version"),
    path("common/", include("common.api.v1.common.urls")),
    path("accounts/", include("common.api.v1.accounts.urls")),
    path("kiosk/", include("common.api.v1.kiosk.urls")),
    path("", include("common.api.v1.stores.urls")),
    path("", include("common.api.v1.orders.urls")),
    path("", include("common.api.v1.payments.urls")),
    path("", include("common.api.v1.fiscal.urls")),
]
