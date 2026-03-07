from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    Product,
    ProductImage,
    ProductVideo,
    ProductPrice,
    Stock,
    Barcode,
)


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    extra = 0
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
    extra = 0
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
    extra = 0
    fields = ("store", "quantity",)


class BarcodeInline(admin.TabularInline):
    model = Barcode
    extra = 1
    fields = ("code", "barcode_type", "is_primary",)
    readonly_fields = ()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "sort_order", "is_active",)
    list_filter = ("is_active",)
    search_fields = ("name", "slug",)
    readonly_fields = ("slug",)
    ordering = ("parent__sort_order", "sort_order",)
    fieldsets = (
        (None, {
            "fields": ("name", "parent", "sort_order", "is_active",),
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
            "fields": ("is_active", "name", "category", "price",),
        }),
        ("Описание", {
            "fields": ("description",),
        }),
    )
    inlines = (BarcodeInline, StockInline, ProductImageInline, ProductVideoInline,)


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ("product", "store", "price", "currency", "effective_from", "effective_to", "is_active",)
    list_filter = ("is_active", "currency", "store",)
    search_fields = ("product__name", "store__name",)
    readonly_fields = ("created_at", "updated_at",)
    ordering = ("-effective_from",)
    fieldsets = (
        (None, {
            "fields": ("product", "store", "price", "currency", "is_active",),
        }),
        ("Период действия", {
            "fields": ("effective_from", "effective_to",),
        }),
        ("Информация", {
            "fields": ("created_at", "updated_at",),
            "classes": ("collapse",),
        }),
    )


@admin.register(Barcode)
class BarcodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "product",
        "barcode_type",
        "is_primary",
        "created_at",
    )
    list_filter = (
        "barcode_type",
        "is_primary",
        "created_at",
    )
    search_fields = (
        "code",
        "product__name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {
            "fields": ("product", "code", "barcode_type", "is_primary"),
        }),
        ("Информация", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    ordering = ("-is_primary", "-created_at")

    def get_readonly_fields(self, request, obj=None):
        """При редактировании кода нельзя изменять."""
        if obj:  # Редактирование существующего объекта
            return self.readonly_fields + ("code",)
        return self.readonly_fields
