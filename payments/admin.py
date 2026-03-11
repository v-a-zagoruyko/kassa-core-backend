from django.contrib import admin

from payments.models import Payment, PaymentMethod, PaymentTransaction


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "display_name")


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = ("id", "transaction_type", "amount", "status", "acquiring_transaction_id", "created_at")
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "amount", "currency", "method", "status", "initiated_at")
    list_filter = ("status", "currency", "method")
    search_fields = ("id", "acquiring_payment_id", "order__id")
    readonly_fields = ("id", "initiated_at", "acquiring_data")
    inlines = [PaymentTransactionInline]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "transaction_type", "amount", "status", "created_at")
    list_filter = ("status", "transaction_type")
    search_fields = ("id", "acquiring_transaction_id", "payment__id")
    readonly_fields = ("id", "created_at", "raw_data")
