"""Jenis pekerjaan per hari kerja (Rencana Kerja v3, permintaan pemilik 2026-10-09).

Revision ID: 0034_plan_day_work_type
Revises: 0033_availability_per_day
Create Date: 2026-10-09

`work_plan_day.work_type_id`: jenis pekerjaan khusus hari itu (NULL = ikut jenis rencana). Template foto laporan dan
foto wajib hari itu mengikuti jenis tersebut.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0034_plan_day_work_type"
down_revision: str | None = "0033_availability_per_day"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan_day ADD COLUMN IF NOT EXISTS work_type_id uuid REFERENCES vms.work_type(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_work_plan_day_work_type_id ON vms.work_plan_day (work_type_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan_day DROP COLUMN IF EXISTS work_type_id")
