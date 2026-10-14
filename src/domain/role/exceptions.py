class RoleNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Role not found: {identifier}")
        self.identifier = identifier
