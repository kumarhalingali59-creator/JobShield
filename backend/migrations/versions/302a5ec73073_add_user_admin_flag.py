"""add user admin flag

Revision ID: 302a5ec73073
Revises: a926dfd6a7ee
Create Date: 2026-10-20 19:19:30.229008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '302a5ec73073'
down_revision: Union[str, Sequence[str], None] = 'a926dfd6a7ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")