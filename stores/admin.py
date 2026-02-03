import json
from decimal import Decimal
from functools import update_wrapper

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, reverse
from common.models import Address
from common.services.dadata_service import DadataService
from .forms import StoreAdminForm
from .models import Store, StoreWorkingHours, StoreSpecialHours
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
    extra = 1
    fields = ("date", "open_time", "close_time",)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    fields = ("product", "quantity",)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    form = StoreAdminForm
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
                wrap(self.address_coordinates_view),
                name="%s_%s_address_coordinates" % info,
            ),
            path(
                "dadata-suggest/",
                wrap(self.dadata_address_suggest_view),
                name="%s_%s_dadata_suggest" % info,
            ),
            path(
                "create-address-from-dadata/",
                wrap(self.create_address_from_dadata_view),
                name="%s_%s_create_address_from_dadata" % info,
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

    def dadata_address_suggest_view(self, request):
        if request.method != "GET":
            return JsonResponse({"error": "method_not_allowed"}, status=405)
        query = (request.GET.get("query") or "").strip()
        if len(query) < 2:
            return JsonResponse([])
        try:
            service = DadataService()
            suggestions = service.suggest_addresses(query=query, count=10)
        except Exception:
            return JsonResponse([])
        result = []
        for s in suggestions:
            data = s.get("data") or {}
            try:
                lat = data.get("geo_lat")
                lat = Decimal(str(lat)) if lat is not None and str(lat).strip() else None
            except (TypeError, ValueError):
                lat = None
            try:
                lon = data.get("geo_lon")
                lon = Decimal(str(lon)) if lon is not None and str(lon).strip() else None
            except (TypeError, ValueError):
                lon = None
            result.append({
                "value": s.get("value") or "",
                "data": {
                    "city": (data.get("city") or "").strip() or None,
                    "street": (data.get("street") or "").strip() or None,
                    "house": (data.get("house") or "").strip() or None,
                    "apartment": (data.get("flat") or "").strip() or None,
                    "latitude": float(lat) if lat is not None else None,
                    "longitude": float(lon) if lon is not None else None,
                },
            })
        return JsonResponse(result, safe=False)

    def create_address_from_dadata_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "method_not_allowed"}, status=405)
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({"error": "invalid_json"}, status=400)
        city = (body.get("city") or "").strip()
        street = (body.get("street") or "").strip()
        house = (body.get("house") or "").strip()
        apartment = (body.get("apartment") or "").strip() or None
        if not city or not street or not house:
            return JsonResponse({"error": "city, street, house required"}, status=400)
        try:
            lat = body.get("latitude")
            lat = Decimal(str(lat)) if lat is not None and str(lat).strip() else None
        except (TypeError, ValueError):
            lat = None
        try:
            lon = body.get("longitude")
            lon = Decimal(str(lon)) if lon is not None and str(lon).strip() else None
        except (TypeError, ValueError):
            lon = None
        address, _ = Address.objects.get_or_create(
            city=city,
            street=street,
            house=house,
            apartment=apartment,
            defaults={"latitude": lat, "longitude": lon},
        )
        return JsonResponse({"address_id": str(address.pk)})

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