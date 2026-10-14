class UserNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"User not found: {identifier}")
        self.identifier = identifier
