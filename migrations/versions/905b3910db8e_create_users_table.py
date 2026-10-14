"""create users table

Revision ID: 905b3910db8e
Revises:
Create Date: 2026-07-01 14:20:32.283633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '905b3910db8e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_subject", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("roles", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_users_external_subject", "users", ["external_subject"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_users_external_subject", table_name="users")
    op.drop_table("users")
