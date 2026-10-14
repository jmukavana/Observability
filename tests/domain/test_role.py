from src.domain.role.entities import Role
from src.domain.role.value_objects import Permission


def test_create_role_has_given_permissions():
    role = Role.create(
        name="Auditor", permissions=frozenset({Permission.parse("claim:view")})
    )

    assert role.name == "Auditor"
    assert role.has_permission(Permission.parse("claim:view"))
    assert not role.has_permission(Permission.parse("claim:approve"))


def test_grant_adds_permission_without_mutating_original():
    role = Role.create(name="Auditor", permissions=frozenset())

    granted = role.grant(Permission.parse("report:view"))

    assert granted.has_permission(Permission.parse("report:view"))
    assert not role.has_permission(Permission.parse("report:view"))


def test_revoke_removes_permission():
    role = Role.create(
        name="Auditor", permissions=frozenset({Permission.parse("report:view")})
    )

    revoked = role.revoke(Permission.parse("report:view"))

    assert not revoked.has_permission(Permission.parse("report:view"))
