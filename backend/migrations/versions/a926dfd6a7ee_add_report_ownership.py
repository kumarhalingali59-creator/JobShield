
"""add report ownership

Revision ID: a926dfd6a7ee
Revises: 3b6027bc9d6a
Create Date: 2026-10-17 00:20:06.580313
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a926dfd6a7ee"
down_revision: Union[str, Sequence[str], None] = "3b6027bc9d6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_reports_user_id"),
        "reports",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_reports_user_id_users",
        "reports",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_reports_user_id_users",
        "reports",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_reports_user_id"),
        table_name="reports",
    )
    op.drop_column("reports", "user_id")
