from django.urls import path, include


urlpatterns = [
    path("common/", include("common.api.v1.common.urls")),
]