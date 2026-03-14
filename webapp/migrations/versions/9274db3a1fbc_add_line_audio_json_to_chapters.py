"""add line_audio_json to chapters

Revision ID: 9274db3a1fbc
Revises: 41ef5721b9d6
Create Date: 2026-03-14 14:41:47.445420

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9274db3a1fbc"
down_revision: str | None = "41ef5721b9d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add line_audio_json column to chapters table."""
    op.add_column("chapters", sa.Column("line_audio_json", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove line_audio_json column from chapters table."""
    op.drop_column("chapters", "line_audio_json")
