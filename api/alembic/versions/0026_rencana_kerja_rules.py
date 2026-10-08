"""Tanda luar kota pada rencana kerja (Rencana Kerja v3, T5, 2026-10-08).

Revision ID: 0026_rencana_kerja_rules
Revises: 0025_rls_remaining_tables
Create Date: 2026-10-08

Nomor dokumen berawalan RK- dibuat di aplikasi (crud_plan_transition), bukan fungsi SQL, jadi tidak ada fungsi
yang diganti. Kolom baru ikut kebijakan RLS tabel work_plan yang sudah ada.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0026_rencana_kerja_rules"
down_revision: str | None = "0025_rls_remaining_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan ADD COLUMN IF NOT EXISTS is_out_of_town boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan DROP COLUMN IF EXISTS is_out_of_town")
