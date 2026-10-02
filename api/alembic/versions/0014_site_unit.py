"""Lokasi kerja per unit (R-33): `site.unit_id` NULL = lokasi kantor (dikelola Finance), terisi = lokasi
proyek milik unit itu (dibuat PM, berlaku untuk bawahannya). Isi awal dari SK terbaru yang memakai lokasi.

Revision ID: 0014_site_unit
Revises: 0013_attendance_mode_web
Create Date: 2026-10-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0014_site_unit"
down_revision: str | Sequence[str] | None = "0013_attendance_mode_web"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("ALTER TABLE site ADD COLUMN unit_id uuid REFERENCES business_unit(id)")
    op.execute("CREATE INDEX site_unit_idx ON site (organization_id, unit_id) WHERE deleted_at IS NULL")
    op.execute(
        """
        UPDATE site s SET unit_id = (
            SELECT wp.unit_id FROM work_plan wp
            WHERE wp.site_id = s.id ORDER BY wp.created_at DESC LIMIT 1)
        """
    )
    op.execute("COMMENT ON COLUMN site.unit_id IS "
               "'NULL = lokasi kantor (Finance); terisi = lokasi proyek unit itu (PM, untuk bawahannya).'")


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("DROP INDEX IF EXISTS site_unit_idx")
    op.execute("ALTER TABLE site DROP COLUMN IF EXISTS unit_id")
