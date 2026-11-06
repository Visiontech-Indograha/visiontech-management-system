"""Keterangan teks per foto kampanye K3 (`media_captions`, sejajar dengan `media_paths`).

Expand-only: hanya menambah kolom JSONB dengan nilai bawaan `[]`. Kampanye lama tanpa keterangan tetap valid.

Revision ID: v2_0023
Revises: v2_0022
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0023"
down_revision: str | None = "v2_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE hse_campaigns ADD COLUMN IF NOT EXISTS media_captions JSONB NOT NULL DEFAULT '[]'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE hse_campaigns DROP COLUMN IF EXISTS media_captions")
