"""Order alokasi (work_completion) lahir dari Work Order yang survei-nya disetujui PM.

Temuan E2E A4: dialog Alokasikan kosong walau survei WO sudah disetujui, karena alokasi membaca `work_completion`
sedangkan WO ("Tugas Klien") tidak pernah membuatnya. Expand murni: kolom NULLABLE `work_completion.work_order_id`
+ indeks unik parsial (satu order per WO, idempoten). Backfill: WO yang sudah disetujui (READY_TO_EXECUTE dst.)
dan belum punya order dibuatkan satu order.

Revision ID: v2_0037
Revises: v2_0036
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0037"
down_revision: str | None = "v2_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE work_completion ADD COLUMN IF NOT EXISTS work_order_id UUID NULL "
        "REFERENCES client_work_orders(work_order_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_work_completion_work_order ON work_completion(work_order_id) "
        "WHERE work_order_id IS NOT NULL AND delete_at IS NULL"
    )
    op.execute(
        """
        INSERT INTO work_completion (report_scope, division_id, pm_id, client_id, client_name, project_title,
                                     order_number, total_target_unit, unit_measure, order_status, priority_level,
                                     work_order_id)
        SELECT 'PROJECT', w.division_id, w.pm_id, w.client_id, c.name, w.title, w.wo_number,
               GREATEST(1, (SELECT COUNT(*) FROM work_order_items i
                            WHERE i.work_order_id = w.work_order_id AND i.delete_at IS NULL))::int,
               'Unit', 'ONGOING', 'NORMAL', w.work_order_id
        FROM client_work_orders w JOIN client c ON c.client_id = w.client_id
        WHERE w.delete_at IS NULL AND w.status IN ('READY_TO_EXECUTE', 'IN_PROGRESS')
          AND NOT EXISTS (SELECT 1 FROM work_completion x
                          WHERE x.work_order_id = w.work_order_id AND x.delete_at IS NULL)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_work_completion_work_order")
    op.execute("ALTER TABLE work_completion DROP COLUMN IF EXISTS work_order_id")
