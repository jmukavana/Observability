from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.role.value_objects import RoleId
from src.domain.user.value_objects import UserId


@dataclass(frozen=True)
class User:
    id: UserId
    external_subject: str
    email: str
    role_ids: frozenset[RoleId]
    created_at: datetime

    @classmethod
    def register(
        cls, external_subject: str, email: str, role_ids: frozenset[RoleId]
    ) -> "User":
        return cls(
            id=UserId(uuid4()),
            external_subject=external_subject,
            email=email,
            role_ids=role_ids,
            created_at=datetime.now(timezone.utc),
        )

    def with_roles(self, role_ids: frozenset[RoleId]) -> "User":
        return replace(self, role_ids=role_ids)
