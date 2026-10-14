from abc import ABC, abstractmethod

from src.domain.role.entities import Role
from src.domain.role.value_objects import RoleId


class RoleRepository(ABC):
    @abstractmethod
    async def add(self, role: Role) -> None: ...

    @abstractmethod
    async def get_by_id(self, role_id: RoleId) -> Role | None: ...

    @abstractmethod
    async def get_by_ids(self, role_ids: frozenset[RoleId]) -> list[Role]: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    async def update(self, role: Role) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[Role]: ...
