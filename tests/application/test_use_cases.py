import pytest

from src.application.user.use_cases import IdentityClaims, ListUsers, SetUserRoles, SyncUserFromIdentity
from src.domain.role.entities import Role
from src.domain.role.exceptions import RoleNotFoundError
from src.domain.role.value_objects import Permission
from src.domain.user.entities import User
from src.domain.user.exceptions import UserNotFoundError
from tests.fakes import InMemoryRoleRepository, InMemoryUserRepository


@pytest.mark.asyncio
async def test_sync_assigns_role_matching_claimed_name():
    member_role = Role.create(name="member", permissions=frozenset())
    admin_role = Role.create(
        name="admin", permissions=frozenset({Permission.parse("user:manage")})
    )
    use_case = SyncUserFromIdentity(
        InMemoryUserRepository(), InMemoryRoleRepository([member_role, admin_role])
    )

    user = await use_case.execute(
        IdentityClaims(
            subject="sub-1", email="a@example.com", claimed_role_names=frozenset({"admin"})
        )
    )

    assert user.role_ids == frozenset({admin_role.id})


@pytest.mark.asyncio
async def test_sync_falls_back_to_member_role_when_no_claim_matches():
    member_role = Role.create(name="member", permissions=frozenset())
    use_case = SyncUserFromIdentity(
        InMemoryUserRepository(), InMemoryRoleRepository([member_role])
    )

    user = await use_case.execute(
        IdentityClaims(
            subject="sub-2",
            email="b@example.com",
            claimed_role_names=frozenset({"unknown-role"}),
        )
    )

    assert user.role_ids == frozenset({member_role.id})


@pytest.mark.asyncio
async def test_sync_returns_existing_user_without_duplicating():
    member_role = Role.create(name="member", permissions=frozenset())
    users = InMemoryUserRepository()
    use_case = SyncUserFromIdentity(users, InMemoryRoleRepository([member_role]))
    claims = IdentityClaims(
        subject="sub-1", email="a@example.com", claimed_role_names=frozenset({"member"})
    )

    first = await use_case.execute(claims)
    second = await use_case.execute(claims)

    assert first.id == second.id
    assert len(await users.list_all()) == 1


@pytest.mark.asyncio
async def test_list_users_returns_all_registered_users():
    users = InMemoryUserRepository()
    await users.add(
        User.register(external_subject="sub-1", email="a@example.com", role_ids=frozenset())
    )
    await users.add(
        User.register(external_subject="sub-2", email="b@example.com", role_ids=frozenset())
    )

    result = await ListUsers(users).execute()

    assert len(result) == 2


@pytest.mark.asyncio
async def test_set_user_roles_replaces_role_ids():
    role = Role.create(name="Auditor", permissions=frozenset())
    users = InMemoryUserRepository()
    user = User.register(external_subject="sub-1", email="a@example.com", role_ids=frozenset())
    await users.add(user)
    roles = InMemoryRoleRepository([role])

    updated = await SetUserRoles(users, roles).execute(user.id, frozenset({role.id}))

    assert updated.role_ids == frozenset({role.id})


@pytest.mark.asyncio
async def test_set_user_roles_raises_when_user_missing():
    role = Role.create(name="Auditor", permissions=frozenset())
    users = InMemoryUserRepository()
    roles = InMemoryRoleRepository([role])
    missing_user_id = User.register(
        external_subject="ghost", email="g@example.com", role_ids=frozenset()
    ).id

    with pytest.raises(UserNotFoundError):
        await SetUserRoles(users, roles).execute(missing_user_id, frozenset({role.id}))


@pytest.mark.asyncio
async def test_set_user_roles_raises_when_role_missing():
    users = InMemoryUserRepository()
    user = User.register(external_subject="sub-1", email="a@example.com", role_ids=frozenset())
    await users.add(user)
    roles = InMemoryRoleRepository([])
    nonexistent_role = Role.create(name="Ghost Role", permissions=frozenset())

    with pytest.raises(RoleNotFoundError):
        await SetUserRoles(users, roles).execute(user.id, frozenset({nonexistent_role.id}))
