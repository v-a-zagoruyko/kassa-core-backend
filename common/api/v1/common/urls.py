from django.urls import path

from .views import DadataAddressSuggestView


urlpatterns = [
    path(
        "dadata/address/suggest/",
        DadataAddressSuggestView.as_view(),
        name="dadata-address-suggest",
    ),
]
