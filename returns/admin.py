from django.contrib import admin

from .models import Return, ReturnItem, ReturnReason, ReturnStatus


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    fields = ('order_item', 'quantity', 'refund_amount')
    readonly_fields = ('order_item',)


class ReturnStatusInline(admin.TabularInline):
    model = ReturnStatus
    extra = 0
    fields = ('status', 'changed_at', 'changed_by', 'comment')
    readonly_fields = ('status', 'changed_at', 'changed_by', 'comment')


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'refund_method', 'total_amount', 'processed_by')
    list_filter = ('status', 'refund_method')
    search_fields = ('id', 'order__id')
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'total_amount')
    inlines = (ReturnItemInline, ReturnStatusInline)


@admin.register(ReturnReason)
class ReturnReasonAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
