from django.urls import include, path


urlpatterns = [
    path("common/", include("common.api.v1.common.urls")),
    path("accounts/", include("common.api.v1.accounts.urls")),
]