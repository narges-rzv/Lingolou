"""add story slug and fix audio path

Revision ID: a1b2c3d4e5f6
Revises: cb49eb5d19de
Create Date: 2026-03-07 12:00:00.000000

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "cb49eb5d19de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add public_id and slug columns to stories, backfill, fix audio_path."""
    # Step 1: Add columns as nullable first
    with op.batch_alter_table("stories") as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("slug", sa.String(100), nullable=True))

    # Step 2: Backfill existing stories with UUID and mnemonic slug
    conn = op.get_bind()
    stories = conn.execute(sa.text("SELECT id FROM stories")).fetchall()

    # Import mnemonic encoding
    from webapp.services.mnemonic import encode

    used_slugs: set[str] = set()
    for (story_id,) in stories:
        # Generate unique UUID + slug
        while True:
            public_id = str(uuid.uuid4())
            slug = encode(public_id)
            if slug not in used_slugs:
                used_slugs.add(slug)
                break

        conn.execute(
            sa.text("UPDATE stories SET public_id = :pid, slug = :slug WHERE id = :sid"),
            {"pid": public_id, "slug": slug, "sid": story_id},
        )

    # Step 3: Make columns non-nullable and add unique indexes
    with op.batch_alter_table("stories") as batch_op:
        batch_op.alter_column("public_id", nullable=False)
        batch_op.alter_column("slug", nullable=False)
        batch_op.create_unique_constraint("uq_stories_public_id", ["public_id"])
        batch_op.create_unique_constraint("uq_stories_slug", ["slug"])
        batch_op.create_index("ix_stories_public_id", ["public_id"])
        batch_op.create_index("ix_stories_slug", ["slug"])

    # Step 4: Fix audio_path — store storage key instead of full URL
    chapters = conn.execute(
        sa.text("SELECT id, story_id, chapter_number, audio_path FROM chapters WHERE audio_path IS NOT NULL")
    ).fetchall()
    for chapter_id, story_id, chapter_number, _audio_path in chapters:
        # Replace full URL or static path with just the storage key
        storage_key = f"{story_id}/ch{chapter_number}.mp3"
        conn.execute(
            sa.text("UPDATE chapters SET audio_path = :key WHERE id = :cid"),
            {"key": storage_key, "cid": chapter_id},
        )


def downgrade() -> None:
    """Remove public_id and slug columns from stories."""
    with op.batch_alter_table("stories") as batch_op:
        batch_op.drop_index("ix_stories_slug")
        batch_op.drop_index("ix_stories_public_id")
        batch_op.drop_constraint("uq_stories_slug", type_="unique")
        batch_op.drop_constraint("uq_stories_public_id", type_="unique")
        batch_op.drop_column("slug")
        batch_op.drop_column("public_id")
