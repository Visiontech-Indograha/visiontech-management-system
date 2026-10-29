"""Jenis jadwal harian `kind` ('WORK' | 'STANDBY') untuk fitur Alokasi mingguan & Service by request.

Default 'WORK' mengisi seluruh baris lama (backfill otomatis oleh ADD COLUMN ... DEFAULT). Idempoten: db/06 sudah
memuat kolom ini untuk pemasangan baru.

Revision ID: v2_0014
Revises: v2_0013
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0014"
down_revision: str | None = "v2_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE work_plan_daily ADD COLUMN IF NOT EXISTS kind VARCHAR(10) NOT NULL DEFAULT 'WORK'")
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE work_plan_daily ADD CONSTRAINT ck_work_plan_daily_kind CHECK (kind IN ('WORK', 'STANDBY'));
        EXCEPTION WHEN duplicate_object THEN NULL; END $$
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE work_plan_daily DROP CONSTRAINT IF EXISTS ck_work_plan_daily_kind")
    op.execute("ALTER TABLE work_plan_daily DROP COLUMN IF EXISTS kind")
