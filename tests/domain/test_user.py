from uuid import uuid4

from src.domain.role.value_objects import RoleId
from src.domain.user.entities import User


def test_register_creates_user_with_given_role_ids():
    role_id = RoleId(uuid4())
    user = User.register(
        external_subject="abc123",
        email="jane@example.com",
        role_ids=frozenset({role_id}),
    )

    assert user.external_subject == "abc123"
    assert user.email == "jane@example.com"
    assert user.role_ids == frozenset({role_id})


def test_with_roles_replaces_role_ids_without_mutating_original():
    original_role_id = RoleId(uuid4())
    new_role_id = RoleId(uuid4())
    user = User.register(
        external_subject="abc123",
        email="jane@example.com",
        role_ids=frozenset({original_role_id}),
    )

    updated = user.with_roles(frozenset({new_role_id}))

    assert updated.role_ids == frozenset({new_role_id})
    assert user.role_ids == frozenset({original_role_id})
