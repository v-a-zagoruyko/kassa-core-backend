from rest_framework.permissions import BasePermission

ADMIN_ROLES = frozenset({'admin', 'root', 'manager'})


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        user_roles = set(
            request.user.roles.filter(is_active=True).values_list('codename', flat=True)
        )
        return bool(user_roles & ADMIN_ROLES)
