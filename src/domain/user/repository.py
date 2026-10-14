from abc import ABC, abstractmethod

from src.domain.user.entities import User
from src.domain.user.value_objects import UserId


class UserRepository(ABC):
    @abstractmethod
    async def get_by_external_subject(self, external_subject: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None: ...

    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...
