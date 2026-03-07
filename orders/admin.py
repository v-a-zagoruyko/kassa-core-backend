from django.contrib import admin

from .models import Order, OrderItem, OrderStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'subtotal', 'marking_code')
    readonly_fields = ('subtotal',)


class OrderStatusInline(admin.TabularInline):
    model = OrderStatus
    extra = 0
    fields = ('status', 'changed_by', 'comment', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'kiosk', 'status', 'total_amount', 'final_amount', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'store')
    search_fields = ('id', 'store__name', 'customer__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (OrderItemInline, OrderStatusInline)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price', 'subtotal')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'product__name', 'marking_code')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'changed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('order__id', 'comment')
    readonly_fields = ('created_at',)
