from uuid import UUID

from sqlmodel import Field, SQLModel, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.role.entities import Role
from src.domain.role.repository import RoleRepository
from src.domain.role.value_objects import Permission, RoleId


class RoleModel(SQLModel, table=True):
    __tablename__ = "roles"

    id: UUID = Field(primary_key=True)
    name: str = Field(unique=True, index=True)
    permissions: str

    def to_entity(self) -> Role:
        return Role(
            id=RoleId(self.id),
            name=self.name,
            permissions=frozenset(
                Permission.parse(authority)
                for authority in self.permissions.split(",")
                if authority
            ),
        )

    @classmethod
    def from_entity(cls, role: Role) -> "RoleModel":
        return cls(
            id=role.id,
            name=role.name,
            permissions=",".join(str(permission) for permission in role.permissions),
        )


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, role: Role) -> None:
        self._session.add(RoleModel.from_entity(role))
        await self._session.commit()

    async def get_by_id(self, role_id: RoleId) -> Role | None:
        model = await self._session.get(RoleModel, role_id)
        return model.to_entity() if model else None

    async def get_by_ids(self, role_ids: frozenset[RoleId]) -> list[Role]:
        if not role_ids:
            return []
        statement = select(RoleModel).where(col(RoleModel.id).in_(role_ids))
        result = await self._session.exec(statement)
        return [model.to_entity() for model in result.all()]

    async def get_by_name(self, name: str) -> Role | None:
        statement = select(RoleModel).where(RoleModel.name == name)
        result = await self._session.exec(statement)
        model = result.first()
        return model.to_entity() if model else None

    async def update(self, role: Role) -> None:
        await self._session.merge(RoleModel.from_entity(role))
        await self._session.commit()

    async def list_all(self) -> list[Role]:
        result = await self._session.exec(select(RoleModel))
        return [model.to_entity() for model in result.all()]
