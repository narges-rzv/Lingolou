"""add display_name to users

Revision ID: 624ccdc8b9a3
Revises: a1b2c3d4e5f6
Create Date: 2026-03-10 16:18:37.850690

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "624ccdc8b9a3"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))
    # Backfill existing users: set display_name = username where not yet set
    op.execute("UPDATE users SET display_name = username WHERE display_name IS NULL")


def downgrade() -> None:
    op.drop_column("users", "display_name")
