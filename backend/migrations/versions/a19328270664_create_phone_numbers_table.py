"""create phone numbers table

Revision ID: a19328270664
Revises: 63bde89be89a
Create Date: 2026-10-13 00:05:07.812318

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a19328270664"
down_revision: Union[str, Sequence[str], None] = "63bde89be89a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "phone_numbers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=False),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )

    op.create_index(
        "ix_phone_numbers_phone_number",
        "phone_numbers",
        ["phone_number"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_phone_numbers_phone_number",
        table_name="phone_numbers",
    )

    op.drop_table("phone_numbers")