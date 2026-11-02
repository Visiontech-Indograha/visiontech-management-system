"""Indikator tugas luar kota pada jadwal harian (`work_plan_daily.is_out_of_town`).

- `work_plan_daily.is_out_of_town` (default FALSE): menandai jadwal tugas luar kota sehingga absensi anggota
  tim pada tanggal itu dihitung zona LUAR_KOTA (tarif uang makan luar kota).

Idempoten: db/06 memuat kolom ini untuk pemasangan baru.

Revision ID: v2_0017
Revises: v2_0016
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0017"
down_revision: str | None = "v2_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE work_plan_daily ADD COLUMN IF NOT EXISTS is_out_of_town BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE work_plan_daily DROP COLUMN IF EXISTS is_out_of_town")
