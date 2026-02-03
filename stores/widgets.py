from django.forms import Widget
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from common.models import Address


class AddressDadataWidget(Widget):
    """Виджет выбора адреса через подсказки Dadata.

    Поле ввода для поиска, под ним readonly-блок с полями Address.
    Валидно только значение, выбранное из подсказок.
    """

    template_name = "admin/stores/widgets/address_dadata_widget.html"
    input_type = "text"

    class Media:
        css = {"all": ("stores/css/address_dadata_widget.css",)}
        js = ("stores/js/address_dadata_widget.js",)

    def __init__(self, attrs=None):
        super().__init__(attrs)
        self._suggest_url = None
        self._create_url = None

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["suggest_url"] = self._get_suggest_url()
        context["widget"]["create_url"] = self._get_create_url()
        context["widget"]["address_display"] = None
        if value:
            try:
                addr = Address.objects.get(pk=value)
                context["widget"]["address_display"] = {
                    "city": addr.city or "",
                    "street": addr.street or "",
                    "house": addr.house or "",
                    "apartment": addr.apartment or "",
                }
            except (Address.DoesNotExist, ValueError):
                pass
        return context

    def _get_suggest_url(self):
        if self._suggest_url is None:
            self._suggest_url = reverse("admin:stores_store_dadata_suggest")
        return self._suggest_url

    def _get_create_url(self):
        if self._create_url is None:
            self._create_url = reverse("admin:stores_store_create_address_from_dadata")
        return self._create_url

    def value_from_datadict(self, data, files, name):
        return data.get(name)
