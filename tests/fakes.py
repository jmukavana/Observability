from src.domain.role.entities import Role
from src.domain.role.repository import RoleRepository
from src.domain.role.value_objects import RoleId
from src.domain.user.entities import User
from src.domain.user.repository import UserRepository
from src.domain.user.value_objects import UserId


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: list[User] = []

    async def get_by_external_subject(self, external_subject: str) -> User | None:
        return next(
            (u for u in self._users if u.external_subject == external_subject), None
        )

    async def get_by_id(self, user_id: UserId) -> User | None:
        return next((u for u in self._users if u.id == user_id), None)

    async def add(self, user: User) -> None:
        self._users.append(user)

    async def update(self, user: User) -> None:
        self._users = [user if u.id == user.id else u for u in self._users]

    async def list_all(self) -> list[User]:
        return list(self._users)


class InMemoryRoleRepository(RoleRepository):
    def __init__(self, roles: list[Role] | None = None) -> None:
        self._roles = list(roles or [])

    async def add(self, role: Role) -> None:
        self._roles.append(role)

    async def get_by_id(self, role_id: RoleId) -> Role | None:
        return next((r for r in self._roles if r.id == role_id), None)

    async def get_by_ids(self, role_ids: frozenset[RoleId]) -> list[Role]:
        return [r for r in self._roles if r.id in role_ids]

    async def get_by_name(self, name: str) -> Role | None:
        return next((r for r in self._roles if r.name == name), None)

    async def update(self, role: Role) -> None:
        self._roles = [role if r.id == role.id else r for r in self._roles]

    async def list_all(self) -> list[Role]:
        return list(self._roles)
