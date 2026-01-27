from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserSettings, UserAddress


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    min_num = 1
    max_num = 1
    can_delete = False
    fields = ("phone",)


class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    min_num = 1
    max_num = 1
    can_delete = False
    fields = ("is_order_push_notifications_enabled", "is_promo_push_notifications_enabled", "is_promo_sms_notifications_enabled", "is_promo_email_notifications_enabled",)
    readonly_fields = ("is_order_push_notifications_enabled", "is_promo_push_notifications_enabled", "is_promo_sms_notifications_enabled", "is_promo_email_notifications_enabled",)

    def has_add_permission(self, request, obj=None):
        return False


class UserAddressInline(admin.StackedInline):
    model = UserAddress
    can_delete = False
    extra = 1
    fields = ("address",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "phone", "is_active",)
    readonly_fields = ("date_joined", "last_login",)
    search_fields = ("username", "email", "profile__phone",)
    ordering = ("-date_joined",)
    inlines = (UserProfileInline, UserSettingsInline, UserAddressInline,)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Телефон")
    def phone(self, obj):
        return obj.profile.phone