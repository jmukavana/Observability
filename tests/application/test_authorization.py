import pytest

from src.application.authorization.use_cases import GetEffectivePermissions
from src.domain.role.entities import Role
from src.domain.role.value_objects import Permission
from src.domain.user.entities import User
from tests.fakes import InMemoryRoleRepository


@pytest.mark.asyncio
async def test_effective_permissions_unions_all_assigned_roles():
    claims_manager = Role.create(
        name="Claims Manager", permissions=frozenset({Permission.parse("claim:create")})
    )
    auditor = Role.create(
        name="Auditor", permissions=frozenset({Permission.parse("report:view")})
    )
    roles = InMemoryRoleRepository([claims_manager, auditor])
    user = User.register(
        external_subject="sub-1",
        email="a@example.com",
        role_ids=frozenset({claims_manager.id, auditor.id}),
    )

    permissions = await GetEffectivePermissions(roles).execute(user)

    assert permissions == frozenset(
        {Permission.parse("claim:create"), Permission.parse("report:view")}
    )


@pytest.mark.asyncio
async def test_effective_permissions_empty_when_user_has_no_roles():
    roles = InMemoryRoleRepository()
    user = User.register(
        external_subject="sub-1", email="a@example.com", role_ids=frozenset()
    )

    permissions = await GetEffectivePermissions(roles).execute(user)

    assert permissions == frozenset()
