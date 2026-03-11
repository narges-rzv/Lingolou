"""add language_level to stories

Revision ID: 41ef5721b9d6
Revises: 624ccdc8b9a3
Create Date: 2026-03-10 16:51:40.878368

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "41ef5721b9d6"
down_revision: str | None = "624ccdc8b9a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("language_level", sa.Integer(), nullable=True))
    # Backfill existing stories with default level 3
    op.execute("UPDATE stories SET language_level = 3 WHERE language_level IS NULL")


def downgrade() -> None:
    op.drop_column("stories", "language_level")
