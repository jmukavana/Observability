from dataclasses import dataclass
from typing import NewType
from uuid import UUID

RoleId = NewType("RoleId", UUID)


@dataclass(frozen=True)
class Permission:
    resource: str
    action: str

    def __post_init__(self) -> None:
        if not self.resource or not self.action:
            raise ValueError(
                f"Permission requires a resource and an action, got {self!r}"
            )

    @classmethod
    def parse(cls, authority: str) -> "Permission":
        resource, separator, action = authority.partition(":")
        if not separator:
            raise ValueError(
                f"Permission must be in 'resource:action' format, got {authority!r}"
            )
        return cls(resource=resource, action=action)

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"
