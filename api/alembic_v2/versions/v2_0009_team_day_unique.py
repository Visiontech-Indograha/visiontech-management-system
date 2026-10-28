"""Satu jadwal harian per tim per tanggal dijamin oleh DB (service hanya memeriksa di muka, rawan balapan).

Revision ID: v2_0009
Revises: v2_0008
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0009"
down_revision: str | None = "v2_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Gagal dengan pesan jelas bila sudah ada duplikat; rapikan datanya dulu (soft-delete salah satunya).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM work_plan_daily WHERE delete_at IS NULL AND team_id IS NOT NULL
                GROUP BY team_id, work_date HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Ada jadwal harian ganda untuk satu tim pada tanggal yang sama; rapikan dulu.';
            END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_work_plan_daily_team_day ON work_plan_daily (team_id, work_date) "
        "WHERE delete_at IS NULL AND team_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_work_plan_daily_team_day")
