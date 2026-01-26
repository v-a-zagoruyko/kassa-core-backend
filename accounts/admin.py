from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserSettings


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    min_num = 1
    max_num = 1
    verbose_name_plural = "Профиль"
    fields = ("phone",)


class UserSettingsInline(admin.TabularInline):
    model = UserSettings
    can_delete = False
    min_num = 1
    max_num = 1
    verbose_name_plural = "Настройки"
    fields = ("is_order_push_notifications_enabled", "is_promo_push_notifications_enabled", "is_promo_sms_notifications_enabled", "is_promo_email_notifications_enabled",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "phone", "is_active",)
    readonly_fields = ("date_joined", "last_login",)
    search_fields = ("username", "email", "profile__phone",)
    ordering = ("-date_joined",)
    inlines = (UserProfileInline, UserSettingsInline,)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Телефон")
    def phone(self, obj):
        return obj.profile.phone