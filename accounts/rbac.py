from rest_framework.permissions import BasePermission


class HasPermission(BasePermission):
    """Usage: permission_classes = [HasPermission("some_codename")]"""

    def __init__(self, codename: str):
        self.codename = codename

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_permission(self.codename)
        )


class HasRole(BasePermission):
    """Usage: permission_classes = [HasRole("some_codename")]"""

    def __init__(self, codename: str):
        self.codename = codename

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(codename=self.codename, is_active=True).exists()
