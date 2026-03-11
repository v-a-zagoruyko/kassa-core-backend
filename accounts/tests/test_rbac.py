import pytest
from unittest.mock import MagicMock
from accounts.models import Permission, Role, RolePermission, User
from accounts.rbac import HasPermission, HasRole


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")


@pytest.fixture
def perm_view(db):
    return Permission.objects.create(name="Can view", codename="can_view")


@pytest.fixture
def perm_edit(db):
    return Permission.objects.create(name="Can edit", codename="can_edit")


@pytest.fixture
def role_with_view(db, perm_view):
    role = Role.objects.create(name="Viewer", codename="viewer")
    RolePermission.objects.create(role=role, permission=perm_view)
    return role


@pytest.mark.django_db
class TestUserHasPermission:
    def test_has_permission_returns_true_for_role_permission(self, user, role_with_view):
        user.roles.add(role_with_view)
        assert user.has_permission("can_view") is True

    def test_has_permission_returns_false_for_missing_permission(self, user, role_with_view):
        user.roles.add(role_with_view)
        assert user.has_permission("can_edit") is False

    def test_has_permission_without_any_roles(self, user):
        assert user.has_permission("can_view") is False

    def test_has_permission_through_inherited_role(self, db, user, perm_view, perm_edit):
        parent = Role.objects.create(name="Parent", codename="parent_role")
        RolePermission.objects.create(role=parent, permission=perm_view)

        child = Role.objects.create(name="Child", codename="child_role", parent=parent)
        RolePermission.objects.create(role=child, permission=perm_edit)

        user.roles.add(child)
        # Child has can_edit directly, can_view via parent
        assert user.has_permission("can_edit") is True
        assert user.has_permission("can_view") is True

    def test_has_permission_inactive_role_excluded(self, user, perm_view):
        role = Role.objects.create(name="Inactive", codename="inactive_role", is_active=False)
        RolePermission.objects.create(role=role, permission=perm_view)
        user.roles.add(role)
        assert user.has_permission("can_view") is False


@pytest.mark.django_db
class TestUserGetAllPermissions:
    def test_get_all_permissions_union_across_roles(self, user, perm_view, perm_edit):
        role1 = Role.objects.create(name="Role1", codename="role1")
        role2 = Role.objects.create(name="Role2", codename="role2")
        RolePermission.objects.create(role=role1, permission=perm_view)
        RolePermission.objects.create(role=role2, permission=perm_edit)

        user.roles.add(role1, role2)
        codenames = set(user.get_all_permissions().values_list("codename", flat=True))
        assert codenames == {"can_view", "can_edit"}

    def test_get_all_permissions_includes_inherited(self, db, user, perm_view, perm_edit):
        parent = Role.objects.create(name="Parent", codename="p_role")
        RolePermission.objects.create(role=parent, permission=perm_view)

        child = Role.objects.create(name="Child", codename="c_role", parent=parent)
        RolePermission.objects.create(role=child, permission=perm_edit)

        user.roles.add(child)
        codenames = set(user.get_all_permissions().values_list("codename", flat=True))
        assert "can_view" in codenames
        assert "can_edit" in codenames

    def test_get_all_permissions_empty_when_no_roles(self, user):
        assert user.get_all_permissions().count() == 0


@pytest.mark.django_db
class TestHasRolePermissionClass:
    def _make_request(self, user):
        request = MagicMock()
        request.user = user
        return request

    def test_has_role_allows_when_user_has_role(self, user):
        role = Role.objects.create(name="Admin", codename="admin", is_active=True)
        user.roles.add(role)
        perm_class = HasRole("admin")
        request = self._make_request(user)
        assert perm_class.has_permission(request, None) is True

    def test_has_role_denies_when_role_missing(self, user):
        perm_class = HasRole("admin")
        request = self._make_request(user)
        assert perm_class.has_permission(request, None) is False

    def test_has_role_denies_when_role_inactive(self, user):
        role = Role.objects.create(name="Admin", codename="admin_inactive", is_active=False)
        user.roles.add(role)
        perm_class = HasRole("admin_inactive")
        request = self._make_request(user)
        assert perm_class.has_permission(request, None) is False

    def test_has_role_denies_unauthenticated(self):
        perm_class = HasRole("admin")
        request = MagicMock()
        request.user = MagicMock(is_authenticated=False)
        assert perm_class.has_permission(request, None) is False


@pytest.mark.django_db
class TestHasPermissionClass:
    def _make_request(self, user):
        request = MagicMock()
        request.user = user
        return request

    def test_has_permission_allows_when_user_has_perm(self, user, role_with_view):
        user.roles.add(role_with_view)
        perm_class = HasPermission("can_view")
        request = self._make_request(user)
        assert perm_class.has_permission(request, None) is True

    def test_has_permission_denies_when_perm_missing(self, user, role_with_view):
        user.roles.add(role_with_view)
        perm_class = HasPermission("can_delete")
        request = self._make_request(user)
        assert perm_class.has_permission(request, None) is False

    def test_has_permission_denies_unauthenticated(self):
        perm_class = HasPermission("can_view")
        request = MagicMock()
        request.user = MagicMock(is_authenticated=False)
        assert perm_class.has_permission(request, None) is False
