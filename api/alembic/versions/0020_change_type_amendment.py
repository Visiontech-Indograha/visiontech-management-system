"""Alur SK v2 PR3 (flowchart SK2-E/F): adendum saat SK Berjalan diajukan ketua (`change_type` AMENDMENT).

Revision ID: 0020_change_type_amendment
Revises: 0019_member_daily_report
Create Date: 2026-10-03
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0020_change_type_amendment"
down_revision: str | Sequence[str] | None = "0019_member_daily_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD VALUE tidak boleh dipakai di transaksi yang sama — jalankan di luar transaksi migrasi.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE vms.change_type ADD VALUE IF NOT EXISTS 'AMENDMENT'")


def downgrade() -> None:
    # PostgreSQL tidak bisa menghapus nilai enum; nilai dibiarkan (tidak dipakai oleh versi lama).
    pass
