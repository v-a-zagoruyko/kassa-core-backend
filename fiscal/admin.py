"""Django Admin для фискального домена."""

from django.contrib import admin

from .models import OFDResponse, Receipt, ReceiptItem, ReceiptStatus


class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 0
    fields = ('product_name', 'quantity', 'price', 'total', 'tax_rate', 'tax_amount')
    readonly_fields = ('total', 'tax_amount')


class OFDResponseInline(admin.TabularInline):
    model = OFDResponse
    extra = 0
    fields = ('status_code', 'response_data', 'error_message', 'created_at')
    readonly_fields = ('status_code', 'response_data', 'error_message', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


class ReceiptStatusInline(admin.TabularInline):
    model = ReceiptStatus
    extra = 0
    fields = ('status', 'comment', 'changed_at')
    readonly_fields = ('status', 'comment', 'changed_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        'receipt_number', 'order', 'status', 'sent_at', 'confirmed_at', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('receipt_number', 'order__id')
    readonly_fields = ('receipt_number', 'fiscal_data', 'ofd_response', 'created_at', 'updated_at')
    inlines = (ReceiptItemInline, ReceiptStatusInline, OFDResponseInline)
    fieldsets = (
        ('Основное', {
            'fields': ('order', 'receipt_number', 'status'),
        }),
        ('Фискальные данные', {
            'fields': ('fiscal_data', 'ofd_response'),
            'classes': ('collapse',),
        }),
        ('Даты', {
            'fields': ('sent_at', 'confirmed_at', 'error_message', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
