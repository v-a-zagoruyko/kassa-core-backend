from functools import update_wrapper

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, reverse

from common.models import Address
from .models import Store, StoreWorkingHours, StoreSpecialHours


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("city", "street", "house", "apartment",)
    fields = ("city", "street", "house", "apartment", "latitude", "longitude",)


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
    extra = 1
    fields = ("date", "open_time", "close_time",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    change_form_template = "admin/stores/store/change_form.html"
    list_display = ("name", "address", "is_active",)
    list_filter = ("is_active",)
    search_fields = ("name", "code",)
    readonly_fields = ("code",)
    fieldsets = (
        (None, {
            "fields": ("code", "name", "address", "delivery_radius_km", "is_active",),
        }),
    )
    inlines = (StoreWorkingHoursInline, StoreSpecialHoursInline,)

    class Media:
        js = ("stores/js/store_map_widget.js",)

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
                wrap(self.address_coordinates_view),
                name="%s_%s_address_coordinates" % info,
            ),
        ]
        return custom + urls

    def address_coordinates_view(self, request, address_id):
        try:
            addr = Address.objects.get(pk=address_id)
        except Address.DoesNotExist:
            return JsonResponse({"error": "not_found"}, status=404)
        return JsonResponse(
            {
                "latitude": str(addr.latitude) if addr.latitude is not None else None,
                "longitude": str(addr.longitude) if addr.longitude is not None else None,
            }
        )

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        store_map_context = {
            "latitude": "",
            "longitude": "",
            "delivery_radius_km": "",
            "address_id": "",
            "address_coordinates_url": "",
        }
        if obj and obj.address_id:
            addr = obj.address
            if addr.latitude is not None and addr.longitude is not None:
                store_map_context["latitude"] = str(addr.latitude)
                store_map_context["longitude"] = str(addr.longitude)
            store_map_context["delivery_radius_km"] = obj.delivery_radius_km
            store_map_context["address_id"] = str(obj.address_id)
        elif obj and getattr(obj, "delivery_radius_km", None) is not None:
            store_map_context["delivery_radius_km"] = obj.delivery_radius_km
        try:
            store_map_context["address_coordinates_url"] = reverse(
                "admin:stores_store_address_coordinates",
                kwargs={"address_id": 0},
                current_app=self.admin_site.name,
            )
        except Exception:
            pass
        context["store_map_context"] = store_map_context
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)