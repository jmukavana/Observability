from dataclasses import dataclass, replace
from uuid import uuid4

from src.domain.role.value_objects import Permission, RoleId


@dataclass(frozen=True)
class Role:
    id: RoleId
    name: str
    permissions: frozenset[Permission]

    @classmethod
    def create(cls, name: str, permissions: frozenset[Permission]) -> "Role":
        return cls(id=RoleId(uuid4()), name=name, permissions=permissions)

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def grant(self, permission: Permission) -> "Role":
        return replace(self, permissions=self.permissions | {permission})

    def revoke(self, permission: Permission) -> "Role":
        return replace(self, permissions=self.permissions - {permission})
