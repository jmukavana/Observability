import pytest

from src.domain.role.value_objects import Permission


def test_parse_splits_resource_and_action():
    permission = Permission.parse("claim:approve")

    assert permission.resource == "claim"
    assert permission.action == "approve"
    assert str(permission) == "claim:approve"


def test_parse_rejects_missing_separator():
    with pytest.raises(ValueError):
        Permission.parse("claimapprove")


def test_construction_rejects_empty_parts():
    with pytest.raises(ValueError):
        Permission(resource="", action="approve")
