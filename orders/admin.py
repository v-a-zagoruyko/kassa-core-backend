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
    list_display = (
        'id', 'store', 'kiosk', 'customer', 'order_type', 'status',
        'delivery_status', 'total_amount', 'delivery_cost', 'final_amount',
        'payment_method', 'created_at',
    )
    list_filter = ('status', 'order_type', 'delivery_status', 'payment_method', 'store')
    search_fields = ('id', 'store__name', 'customer__email')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('delivery_address',)
    inlines = (OrderItemInline, OrderStatusInline)
    fieldsets = (
        ('Основное', {
            'fields': ('store', 'kiosk', 'customer', 'status', 'order_type', 'payment_method'),
        }),
        ('Доставка', {
            'fields': (
                'delivery_address', 'delivery_status', 'delivery_cost',
                'estimated_delivery_at', 'delivered_at', 'courier_comment',
            ),
            'classes': ('collapse',),
        }),
        ('Финансы', {
            'fields': ('total_amount', 'discount_amount', 'final_amount', 'completed_at'),
        }),
        ('Системное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


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
