"""Alur SK v2 (keputusan pemilik 2026-10-03, flowchart SK2 di FigJam): data untuk form "Buat SK" lengkap.

- `work_plan.category`: kategori pekerjaan (daftar tetap). Tipe = nama unit PM, tidak disimpan ulang.
- `work_plan_task.description` + `work_plan_task_attachment`: detail pekerjaan per hari (judul, deskripsi,
  foto/PDF opsional).
- `site.description`: deskripsi lokasi baru yang dibuat dari modal peta.
- `notification`: notifikasi dalam aplikasi (web lonceng, HP daftar) — tanpa Firebase.
- `employee_is_bound()`: "tidak terikat SK" = bukan ketua/anggota/driver SK aktif mana pun, tanpa melihat tanggal.

Revision ID: 0018_work_plan_flow_v2
Revises: 0017_offline_attendance
Create Date: 2026-10-03
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0018_work_plan_flow_v2"
down_revision: str | Sequence[str] | None = "0017_offline_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(
        "ALTER TABLE work_plan ADD COLUMN category text "
        "CHECK (category IN ('INSTALASI','PEMELIHARAAN','PERBAIKAN','SURVEI','LAINNYA'))"
    )
    op.execute("ALTER TABLE work_plan_task ADD COLUMN description text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE site ADD COLUMN description text")
    op.execute(
        """
        CREATE TABLE work_plan_task_attachment (
          task_id     uuid NOT NULL REFERENCES work_plan_task(id) ON DELETE CASCADE,
          file_id     uuid NOT NULL REFERENCES file_object(id),
          sort_order  integer NOT NULL DEFAULT 0,
          PRIMARY KEY (task_id, file_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE notification (
          id                    uuid PRIMARY KEY DEFAULT new_id(),
          organization_id       uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
          recipient_employee_id uuid NOT NULL REFERENCES employee(id) ON DELETE CASCADE,
          kind                  text NOT NULL,
          title                 text NOT NULL,
          body                  text NOT NULL DEFAULT '',
          work_plan_id          uuid REFERENCES work_plan(id) ON DELETE CASCADE,
          created_at            timestamptz NOT NULL DEFAULT now(),
          read_at               timestamptz
        )
        """
    )
    op.execute("CREATE INDEX notification_recipient_idx ON notification (recipient_employee_id, read_at, created_at DESC)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION employee_is_bound(p_employee uuid, p_exclude_plan uuid DEFAULT NULL)
        RETURNS boolean LANGUAGE sql STABLE AS $$
          SELECT EXISTS (
            SELECT 1 FROM work_plan wp
            WHERE wp.deleted_at IS NULL
              AND wp.status IN ('PUBLISHED','APPEALED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
              AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
              AND (EXISTS (SELECT 1 FROM work_plan_member m
                           WHERE m.work_plan_id = wp.id AND m.employee_id = p_employee AND upper_inf(m.valid_period))
                   OR EXISTS (SELECT 1 FROM asset_allocation al
                              WHERE al.work_plan_id = wp.id AND al.driver_employee_id = p_employee
                                AND al.released_at IS NULL))
          )
        $$
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON vms.work_plan_task_attachment TO vms_app;
            GRANT SELECT, INSERT, UPDATE ON vms.notification TO vms_app;
            GRANT EXECUTE ON FUNCTION vms.employee_is_bound(uuid, uuid) TO vms_app;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_readonly') THEN
            GRANT SELECT ON vms.work_plan_task_attachment, vms.notification TO vms_readonly;
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("DROP FUNCTION IF EXISTS employee_is_bound(uuid, uuid)")
    op.execute("DROP TABLE IF EXISTS notification")
    op.execute("DROP TABLE IF EXISTS work_plan_task_attachment")
    op.execute("ALTER TABLE site DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE work_plan_task DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE work_plan DROP COLUMN IF EXISTS category")
