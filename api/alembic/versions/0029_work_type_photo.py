"""Jenis pekerjaan + template foto laporan + sumber/slot foto bukti (Rencana Kerja v3, T9, 2026-10-08).

Revision ID: 0029_work_type_photo
Revises: 0028_attendance_checkout_city
Create Date: 2026-10-08

- `work_type` (jenis pekerjaan, mis. Replacement/Survei) dan `work_type_photo` (slot foto: label, petunjuk, wajib).
- `work_plan.work_type_id` (opsional); kolom `category` lama tetap.
- `report_evidence` / `member_report_evidence`: `slot_label` (slot template yang dipenuhi) dan `source`
  (CAMERA bertanda air atau GALLERY).
Pagar RLS tenant untuk dua tabel baru (child `work_type_photo` membawa organization_id sendiri).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0029_work_type_photo"
down_revision: str | None = "0028_attendance_checkout_city"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE vms.work_type (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id uuid NOT NULL REFERENCES vms.organization(id) ON DELETE CASCADE,
            name            text NOT NULL,
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX work_type_name_uidx ON vms.work_type (organization_id, lower(name))")
    op.execute(
        """
        CREATE TABLE vms.work_type_photo (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id uuid NOT NULL REFERENCES vms.organization(id) ON DELETE CASCADE,
            work_type_id    uuid NOT NULL REFERENCES vms.work_type(id) ON DELETE CASCADE,
            sort_order      integer NOT NULL,
            label           text NOT NULL,
            hint            text,
            required        boolean NOT NULL DEFAULT false
        )
        """
    )
    op.execute("CREATE INDEX ix_work_type_photo_work_type_id ON vms.work_type_photo (work_type_id)")
    op.execute("CREATE INDEX ix_work_type_photo_organization_id ON vms.work_type_photo (organization_id)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON vms.work_type, vms.work_type_photo TO vms_api")
    for table in ("work_type", "work_type_photo"):
        op.execute(f"ALTER TABLE vms.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_isolation ON vms.{table} USING (organization_id = vms.current_org_id())")
    op.execute("ALTER TABLE vms.work_plan ADD COLUMN IF NOT EXISTS work_type_id uuid REFERENCES vms.work_type(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_work_plan_work_type_id ON vms.work_plan (work_type_id)")
    for table in ("report_evidence", "member_report_evidence"):
        op.execute(f"ALTER TABLE vms.{table} ADD COLUMN IF NOT EXISTS slot_label text")
        op.execute(
            f"ALTER TABLE vms.{table} ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'CAMERA' "
            f"CHECK (source IN ('CAMERA','GALLERY'))"
        )


def downgrade() -> None:
    for table in ("report_evidence", "member_report_evidence"):
        op.execute(f"ALTER TABLE vms.{table} DROP COLUMN IF EXISTS source")
        op.execute(f"ALTER TABLE vms.{table} DROP COLUMN IF EXISTS slot_label")
    op.execute("ALTER TABLE vms.work_plan DROP COLUMN IF EXISTS work_type_id")
    op.execute("DROP TABLE IF EXISTS vms.work_type_photo")
    op.execute("DROP TABLE IF EXISTS vms.work_type")
