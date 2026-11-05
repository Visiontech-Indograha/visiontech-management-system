"""Kampanye K3 bergambar banyak (carousel): daftar foto `media_paths` (id file_object, urutan tampil).

Expand-only: hanya menambah kolom JSONB dengan nilai bawaan `[]`. Kolom `media_path` lama tetap dipakai
sebagai cadangan (foto pertama) agar klien lama tetap berfungsi. Durasi baca memakai `cooldown_seconds`
yang sudah ada, sehingga tidak ada kolom durasi baru.

Revision ID: v2_0021
Revises: v2_0020
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0021"
down_revision: str | None = "v2_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE hse_campaigns ADD COLUMN IF NOT EXISTS media_paths JSONB NOT NULL DEFAULT '[]'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE hse_campaigns DROP COLUMN IF EXISTS media_paths")
