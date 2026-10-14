from dataclasses import dataclass

from src.domain.role.exceptions import RoleNotFoundError
from src.domain.role.repository import RoleRepository
from src.domain.role.value_objects import RoleId
from src.domain.user.entities import User
from src.domain.user.exceptions import UserNotFoundError
from src.domain.user.repository import UserRepository
from src.domain.user.value_objects import UserId

DEFAULT_ROLE_NAME = "member"


@dataclass(frozen=True)
class IdentityClaims:
    subject: str
    email: str
    claimed_role_names: frozenset[str]


class SyncUserFromIdentity:
    def __init__(self, users: UserRepository, roles: RoleRepository) -> None:
        self._users = users
        self._roles = roles

    async def execute(self, claims: IdentityClaims) -> User:
        existing = await self._users.get_by_external_subject(claims.subject)
        if existing is not None:
            return existing

        user = User.register(
            external_subject=claims.subject,
            email=claims.email,
            role_ids=await self._resolve_bootstrap_role_ids(claims.claimed_role_names),
        )
        await self._users.add(user)
        return user

    async def _resolve_bootstrap_role_ids(
        self, claimed_role_names: frozenset[str]
    ) -> frozenset[RoleId]:
        matched_roles = []
        for name in claimed_role_names:
            role = await self._roles.get_by_name(name)
            if role is not None:
                matched_roles.append(role)

        if not matched_roles:
            default_role = await self._roles.get_by_name(DEFAULT_ROLE_NAME)
            if default_role is not None:
                matched_roles.append(default_role)

        return frozenset(role.id for role in matched_roles)


class ListUsers:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self) -> list[User]:
        return await self._users.list_all()


class SetUserRoles:
    def __init__(self, users: UserRepository, roles: RoleRepository) -> None:
        self._users = users
        self._roles = roles

    async def execute(self, user_id: UserId, role_ids: frozenset[RoleId]) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        found_roles = await self._roles.get_by_ids(role_ids)
        if len(found_roles) != len(role_ids):
            raise RoleNotFoundError(", ".join(str(role_id) for role_id in role_ids))

        updated = user.with_roles(role_ids)
        await self._users.update(updated)
        return updated
