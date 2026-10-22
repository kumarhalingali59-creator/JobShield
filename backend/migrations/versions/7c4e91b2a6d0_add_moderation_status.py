"""add moderation status to public records

Revision ID: 7c4e91b2a6d0
Revises: 302a5ec73073
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7c4e91b2a6d0"
down_revision: Union[str, Sequence[str], None] = "302a5ec73073"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("companies", "recruiters", "emails", "phone_numbers")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "moderation_status",
                sa.String(length=20),
                nullable=False,
                server_default="approved",
            ),
        )
        op.alter_column(
            table,
            "moderation_status",
            existing_type=sa.String(length=20),
            existing_nullable=False,
            server_default=sa.text("'pending'"),
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_column(table, "moderation_status")
