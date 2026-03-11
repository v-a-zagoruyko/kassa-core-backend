import pytest
from accounts.models import Permission, Role, RolePermission


@pytest.mark.django_db
class TestRoleCreation:
    def test_create_role(self):
        role = Role.objects.create(name="Admin", codename="admin")
        assert role.pk is not None
        assert role.codename == "admin"
        assert role.is_active is True
        assert role.parent is None

    def test_create_role_with_parent(self):
        parent = Role.objects.create(name="Parent", codename="parent")
        child = Role.objects.create(name="Child", codename="child", parent=parent)
        assert child.parent == parent


@pytest.mark.django_db
class TestRoleHierarchy:
    def test_child_inherits_parent_permissions(self):
        perm1 = Permission.objects.create(name="Can view", codename="can_view")
        perm2 = Permission.objects.create(name="Can edit", codename="can_edit")

        parent = Role.objects.create(name="Parent", codename="parent_role")
        RolePermission.objects.create(role=parent, permission=perm1)

        child = Role.objects.create(name="Child", codename="child_role", parent=parent)
        RolePermission.objects.create(role=child, permission=perm2)

        all_perms = child.get_all_permissions()
        codenames = set(all_perms.values_list("codename", flat=True))
        assert "can_view" in codenames
        assert "can_edit" in codenames

    def test_only_own_permissions_without_parent(self):
        perm = Permission.objects.create(name="Can delete", codename="can_delete")
        role = Role.objects.create(name="Solo", codename="solo")
        RolePermission.objects.create(role=role, permission=perm)

        all_perms = role.get_all_permissions()
        assert all_perms.count() == 1
        assert all_perms.first().codename == "can_delete"

    def test_deep_hierarchy_permissions(self):
        perm_root = Permission.objects.create(name="Root perm", codename="root_perm")
        perm_mid = Permission.objects.create(name="Mid perm", codename="mid_perm")
        perm_leaf = Permission.objects.create(name="Leaf perm", codename="leaf_perm")

        root = Role.objects.create(name="Root", codename="root")
        mid = Role.objects.create(name="Mid", codename="mid", parent=root)
        leaf = Role.objects.create(name="Leaf", codename="leaf", parent=mid)

        RolePermission.objects.create(role=root, permission=perm_root)
        RolePermission.objects.create(role=mid, permission=perm_mid)
        RolePermission.objects.create(role=leaf, permission=perm_leaf)

        all_perms = leaf.get_all_permissions()
        codenames = set(all_perms.values_list("codename", flat=True))
        assert codenames == {"root_perm", "mid_perm", "leaf_perm"}


@pytest.mark.django_db
class TestGetAncestors:
    def test_no_ancestors_for_root(self):
        root = Role.objects.create(name="Root", codename="root_anc")
        assert root.get_ancestors() == []

    def test_single_ancestor(self):
        parent = Role.objects.create(name="Parent", codename="par_anc")
        child = Role.objects.create(name="Child", codename="chd_anc", parent=parent)
        ancestors = child.get_ancestors()
        assert len(ancestors) == 1
        assert ancestors[0] == parent

    def test_chain_of_ancestors(self):
        grandparent = Role.objects.create(name="Grandparent", codename="gp_anc")
        parent = Role.objects.create(name="Parent", codename="p_anc", parent=grandparent)
        child = Role.objects.create(name="Child", codename="c_anc", parent=parent)

        ancestors = child.get_ancestors()
        assert ancestors == [parent, grandparent]
