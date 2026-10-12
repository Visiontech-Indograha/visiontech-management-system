"""Ambang kemiripan wajah 0.65 → 0.55 (permintaan pemilik 2026-10-11).

Revision ID: 0036_face_threshold
Revises: 0035_city_center
Create Date: 2026-10-11

Pemilik memutuskan 55% kemiripan sudah cukup untuk match wajah.
- Ubah default kolom untuk organization baru
- Update semua organization existing yang masih pakai 0.65
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0036_face_threshold"
down_revision: str | None = "0035_city_center"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Update default untuk organization baru
    op.execute("ALTER TABLE vms.organization ALTER COLUMN face_match_threshold SET DEFAULT 0.5500")
    # Update semua organization yang masih pakai nilai lama (0.65)
    op.execute("UPDATE vms.organization SET face_match_threshold = 0.5500 WHERE face_match_threshold = 0.6500")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.organization ALTER COLUMN face_match_threshold SET DEFAULT 0.6500")
    op.execute("UPDATE vms.organization SET face_match_threshold = 0.6500 WHERE face_match_threshold = 0.5500")
