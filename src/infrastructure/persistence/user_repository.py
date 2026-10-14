from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.role.value_objects import RoleId
from src.domain.user.entities import User
from src.domain.user.repository import UserRepository
from src.domain.user.value_objects import UserId


class UserModel(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(primary_key=True)
    external_subject: str = Field(unique=True, index=True)
    email: str
    role_ids: str
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))

    def to_entity(self) -> User:
        return User(
            id=UserId(self.id),
            external_subject=self.external_subject,
            email=self.email,
            role_ids=frozenset(
                RoleId(UUID(role_id))
                for role_id in self.role_ids.split(",")
                if role_id
            ),
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            external_subject=user.external_subject,
            email=user.email,
            role_ids=",".join(str(role_id) for role_id in user.role_ids),
            created_at=user.created_at,
        )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_external_subject(self, external_subject: str) -> User | None:
        statement = select(UserModel).where(
            UserModel.external_subject == external_subject
        )
        result = await self._session.exec(statement)
        model = result.first()
        return model.to_entity() if model else None

    async def get_by_id(self, user_id: UserId) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return model.to_entity() if model else None

    async def add(self, user: User) -> None:
        self._session.add(UserModel.from_entity(user))
        await self._session.commit()

    async def update(self, user: User) -> None:
        await self._session.merge(UserModel.from_entity(user))
        await self._session.commit()

    async def list_all(self) -> list[User]:
        result = await self._session.exec(select(UserModel))
        return [model.to_entity() for model in result.all()]
