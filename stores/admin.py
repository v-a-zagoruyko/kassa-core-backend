from django.contrib import admin
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