from src.domain.role.repository import RoleRepository
from src.domain.role.value_objects import Permission
from src.domain.user.entities import User


class GetEffectivePermissions:
    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    async def execute(self, user: User) -> frozenset[Permission]:
        roles = await self._roles.get_by_ids(user.role_ids)
        permissions: frozenset[Permission] = frozenset()
        for role in roles:
            permissions |= role.permissions
        return permissions
