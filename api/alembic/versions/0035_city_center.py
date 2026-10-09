"""Kategori Dalam/Luar kota dari jarak titik absen ke pusat kota organisasi (permintaan pemilik 2026-10-09).

Revision ID: 0035_city_center
Revises: 0034_plan_day_work_type
Create Date: 2026-10-09

- `organization.city_name`, `organization.city_center`, `organization.city_radius_km` (bawaan 60 km): titik absen
  lebih jauh dari radius → LUAR_KOTA, selain itu DALAM_KOTA (mis. kantor Duri/Dumai dari pusat Pekanbaru = luar kota).
- `attendance_city_category_at(org, lokasi)`: NULL bila pusat kota belum diatur atau absen tanpa titik (mesin) —
  pemanggil lalu memakai aturan lama (`attendance_city_category`: rencana kerja bertanda luar kota).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0035_city_center"
down_revision: str | None = "0034_plan_day_work_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FN = """
CREATE OR REPLACE FUNCTION vms.attendance_city_category_at(p_org uuid, p_location geography) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
  SELECT CASE WHEN ST_Distance(p_location, o.city_center) > o.city_radius_km * 1000.0
              THEN 'LUAR_KOTA' ELSE 'DALAM_KOTA' END
  FROM vms.organization o
  WHERE o.id = p_org AND o.id = vms.current_org_id() AND o.city_center IS NOT NULL AND p_location IS NOT NULL
$$
"""


def upgrade() -> None:
    op.execute("ALTER TABLE vms.organization ADD COLUMN IF NOT EXISTS city_name text")
    op.execute("ALTER TABLE vms.organization ADD COLUMN IF NOT EXISTS city_center geography(Point,4326)")
    op.execute("ALTER TABLE vms.organization ADD COLUMN IF NOT EXISTS city_radius_km integer NOT NULL DEFAULT 60 "
               "CHECK (city_radius_km BETWEEN 1 AND 1000)")
    op.execute(_FN)
    op.execute("GRANT EXECUTE ON FUNCTION vms.attendance_city_category_at(uuid, geography) TO vms_api")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS vms.attendance_city_category_at(uuid, geography)")
    op.execute("ALTER TABLE vms.organization DROP COLUMN IF EXISTS city_radius_km")
    op.execute("ALTER TABLE vms.organization DROP COLUMN IF EXISTS city_center")
    op.execute("ALTER TABLE vms.organization DROP COLUMN IF EXISTS city_name")
