from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    Product,
    ProductImage,
    ProductVideo,
    Stock,
)


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("image_preview",)
    fields = ("image_preview", "image", "sort_order",)

    def image_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; object-fit: contain;">',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "Превью"


class ProductVideoInline(admin.StackedInline):
    model = ProductVideo
    extra = 1
    readonly_fields = ("file_preview",)
    fields = ("file_preview", "file", "sort_order",)

    def file_preview(self, obj):
        if obj.pk and obj.file:
            return format_html(
                '<video src="{}" controls style="max-height: 120px; max-width: 240px;"></video>',
                obj.file.url,
            )
        return "—"

    file_preview.short_description = "Превью"


class StockInline(admin.TabularInline):
    model = Stock
    extra = 1
    fields = ("store", "quantity",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "sort_order", "is_active",)
    list_filter = ("is_active",)
    search_fields = ("name", "slug",)
    readonly_fields = ("slug",)
    ordering = ("parent__sort_order", "sort_order",)
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "parent", "sort_order", "is_active",),
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active",)
    list_filter = ("is_active", "category",)
    search_fields = ("name", "slug",)
    readonly_fields = ("slug",)
    ordering = ("category__parent__sort_order", "category__sort_order",)
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "category", "price", "is_active",),
        }),
        ("Описание", {
            "fields": ("description",),
        }),
    )
    inlines = (ProductImageInline, ProductVideoInline, StockInline)
