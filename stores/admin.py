from functools import update_wrapper

from django.contrib import admin
from django.urls import path

from . import admin_views
from .forms import StoreAdminForm
from .models import Store, StoreWorkingHours, StoreSpecialHours
from .context import get_store_map_context
from products.models import Stock


class StoreWorkingHoursInline(admin.StackedInline):
    model = StoreWorkingHours
    can_delete = False
    extra = 7
    min_num = 7
    max_num = 7
    fields = ("day_of_week", "open_time", "close_time",)


class StoreSpecialHoursInline(admin.StackedInline):
    model = StoreSpecialHours
    can_delete = True
    extra = 0
    fields = ("date", "open_time", "close_time",)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ("product", "quantity",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    form = StoreAdminForm
    change_form_template = "admin/stores/store/change_form.html"
    list_display = ("name", "address", "is_active",)
    list_filter = ("is_active",)
    search_fields = ("name", "code",)
    fieldsets = (
        (None, {
            "fields": ("is_active", "name", "address", "delivery_radius_km",),
        }),
    )
    inlines = (StockInline, StoreWorkingHoursInline, StoreSpecialHoursInline,)

    class Media:
        css = {"all": ("stores/css/address_dadata_widget.css",)}
        js = ("stores/js/store_map_widget.js", "stores/js/address_dadata_widget.js",)

    def get_urls(self):
        urls = super().get_urls()
        info = self.opts.app_label, self.opts.model_name

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        custom = [
            path(
                "address-coordinates/<int:address_id>/",
                wrap(admin_views.address_coordinates_view),
                name="%s_%s_address_coordinates" % info,
            ),
            path(
                "dadata-suggest/",
                wrap(admin_views.dadata_address_suggest_view),
                name="%s_%s_dadata_suggest" % info,
            ),
            path(
                "create-address-from-dadata/",
                wrap(admin_views.create_address_from_dadata_view),
                name="%s_%s_create_address_from_dadata" % info,
            ),
        ]
        return custom + urls

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context["store_map_context"] = get_store_map_context(obj, admin_site=self.admin_site)
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)