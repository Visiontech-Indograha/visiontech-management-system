"""Lokasi dan anggota per hari kerja (Rencana Kerja v3, permintaan pemilik 2026-10-09).

Revision ID: 0031_plan_day_site_members
Revises: 0030_work_type_photo_example
Create Date: 2026-10-09

- `work_plan_day.site_id`: lokasi khusus hari itu (NULL = ikut lokasi rencana). Absensi hari itu mengikuti lokasi ini.
- `work_plan_day_member`: anggota yang bertugas pada hari itu. Tanpa baris = seluruh tim rencana; ada baris = hanya yang
  terdaftar (ketua selalu ikut). Tim rencana (`work_plan_member`) tidak berubah: anggota tetap tercatat di rencana.
Pagar RLS tenant untuk tabel baru.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0031_plan_day_site_members"
down_revision: str | None = "0030_work_type_photo_example"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan_day ADD COLUMN IF NOT EXISTS site_id uuid REFERENCES vms.site(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_work_plan_day_site_id ON vms.work_plan_day (site_id)")
    op.execute(
        """
        CREATE TABLE vms.work_plan_day_member (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id  uuid NOT NULL REFERENCES vms.organization(id) ON DELETE CASCADE,
            work_plan_day_id uuid NOT NULL REFERENCES vms.work_plan_day(id) ON DELETE CASCADE,
            employee_id      uuid NOT NULL REFERENCES vms.employee(id),
            UNIQUE (work_plan_day_id, employee_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_work_plan_day_member_employee_id ON vms.work_plan_day_member (employee_id)")
    op.execute("CREATE INDEX ix_work_plan_day_member_organization_id ON vms.work_plan_day_member (organization_id)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON vms.work_plan_day_member TO vms_api")
    op.execute("ALTER TABLE vms.work_plan_day_member ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY work_plan_day_member_isolation ON vms.work_plan_day_member "
        "USING (organization_id = vms.current_org_id())"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vms.work_plan_day_member")
    op.execute("ALTER TABLE vms.work_plan_day DROP COLUMN IF EXISTS site_id")
