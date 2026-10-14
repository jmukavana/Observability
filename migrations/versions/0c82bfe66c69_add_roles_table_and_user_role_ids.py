"""add roles table and user role_ids

Revision ID: 0c82bfe66c69
Revises: 905b3910db8e
Create Date: 2026-07-01 15:37:39.687547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0c82bfe66c69'
down_revision: Union[str, Sequence[str], None] = '905b3910db8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Fixed IDs so the built-in roles are referenceable (e.g. from docs/curl examples)
# without a lookup, and so SyncUserFromIdentity's Keycloak-role bootstrap can match
# "admin"/"member" role names literally against these seeded rows.
ADMIN_ROLE_ID = "6f9496ec-964d-4523-913a-68792cd6e71b"
MEMBER_ROLE_ID = "de718260-0ba7-4df6-b629-201f545b7a39"
CLAIMS_MANAGER_ROLE_ID = "0c2102a2-32dc-4a5e-89bb-acec9e8a8915"
AUDITOR_ROLE_ID = "303c451e-2b00-4e2c-a235-147144198141"


def upgrade() -> None:
    roles_table = op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("permissions", sa.String(), nullable=False),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.bulk_insert(
        roles_table,
        [
            {
                "id": ADMIN_ROLE_ID,
                "name": "admin",
                "permissions": "role:manage,user:manage",
            },
            {"id": MEMBER_ROLE_ID, "name": "member", "permissions": ""},
            {
                "id": CLAIMS_MANAGER_ROLE_ID,
                "name": "Claims Manager",
                "permissions": "claim:create,claim:approve,claim:view",
            },
            {
                "id": AUDITOR_ROLE_ID,
                "name": "Auditor",
                "permissions": "claim:view,report:view",
            },
        ],
    )

    op.add_column("users", sa.Column("role_ids", sa.String(), nullable=True))
    op.execute(
        f"UPDATE users SET role_ids = '{ADMIN_ROLE_ID}' WHERE roles LIKE '%admin%'"
    )
    op.execute(f"UPDATE users SET role_ids = '{MEMBER_ROLE_ID}' WHERE role_ids IS NULL")
    op.alter_column("users", "role_ids", nullable=False)
    op.drop_column("users", "roles")


def downgrade() -> None:
    op.add_column("users", sa.Column("roles", sa.String(), nullable=True))
    op.execute("UPDATE users SET roles = 'member'")
    op.alter_column("users", "roles", nullable=False)
    op.drop_column("users", "role_ids")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
