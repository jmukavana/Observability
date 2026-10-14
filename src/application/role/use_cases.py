from src.domain.role.entities import Role
from src.domain.role.exceptions import RoleNotFoundError
from src.domain.role.repository import RoleRepository
from src.domain.role.value_objects import Permission, RoleId


class CreateRole:
    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    async def execute(self, name: str, permissions: frozenset[Permission]) -> Role:
        role = Role.create(name=name, permissions=permissions)
        await self._roles.add(role)
        return role


class UpdateRolePermissions:
    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    async def execute(
        self,
        role_id: RoleId,
        grant: frozenset[Permission] = frozenset(),
        revoke: frozenset[Permission] = frozenset(),
    ) -> Role:
        role = await self._roles.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))

        for permission in grant:
            role = role.grant(permission)
        for permission in revoke:
            role = role.revoke(permission)

        await self._roles.update(role)
        return role


class ListRoles:
    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    async def execute(self) -> list[Role]:
        return await self._roles.list_all()
