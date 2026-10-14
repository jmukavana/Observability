import pytest

from src.application.role.use_cases import CreateRole, ListRoles, UpdateRolePermissions
from src.domain.role.entities import Role
from src.domain.role.exceptions import RoleNotFoundError
from src.domain.role.value_objects import Permission
from tests.fakes import InMemoryRoleRepository


@pytest.mark.asyncio
async def test_create_role_persists_role_with_given_permissions():
    roles = InMemoryRoleRepository()

    role = await CreateRole(roles).execute(
        "Claims Manager", frozenset({Permission.parse("claim:create")})
    )

    assert role.name == "Claims Manager"
    assert await roles.get_by_id(role.id) is not None


@pytest.mark.asyncio
async def test_update_role_permissions_grants_and_revokes():
    role = Role.create(name="Auditor", permissions=frozenset({Permission.parse("claim:view")}))
    roles = InMemoryRoleRepository([role])

    updated = await UpdateRolePermissions(roles).execute(
        role.id,
        grant=frozenset({Permission.parse("report:view")}),
        revoke=frozenset({Permission.parse("claim:view")}),
    )

    assert updated.has_permission(Permission.parse("report:view"))
    assert not updated.has_permission(Permission.parse("claim:view"))


@pytest.mark.asyncio
async def test_update_role_permissions_raises_when_role_missing():
    roles = InMemoryRoleRepository()
    nonexistent_role = Role.create(name="Ghost Role", permissions=frozenset())

    with pytest.raises(RoleNotFoundError):
        await UpdateRolePermissions(roles).execute(
            nonexistent_role.id, grant=frozenset({Permission.parse("report:view")})
        )


@pytest.mark.asyncio
async def test_list_roles_returns_all_roles():
    roles = InMemoryRoleRepository(
        [
            Role.create(name="Claims Manager", permissions=frozenset()),
            Role.create(name="Auditor", permissions=frozenset()),
        ]
    )

    result = await ListRoles(roles).execute()

    assert len(result) == 2
