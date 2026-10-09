"""Absen pulang di luar radius + kategori dalam/luar kota (Rencana Kerja v3, T7, 2026-10-08).

Revision ID: 0028_attendance_checkout_city
Revises: 0027_plan_revision
Create Date: 2026-10-08

- Kolom lokasi/jarak/swafoto/penjelasan pulang pada `vms.attendance`.
- `tg_attendance_checkout` (BEFORE UPDATE) menghitung jarak pulang di SERVER (aturan inti #3). Di luar radius:
  swafoto + penjelasan wajib (kecuali absen luring yang sudah terjadi: `app.relax_checkout`), dan absen yang tadinya
  Valid otomatis menjadi Perlu review (keputusan pemilik 2026-10-08 #4). Definer + filter organisasi sendiri.
- `attendance_city_category(employee, date)`: kategori dihitung SAAT DIBACA dari rencana kerja luar kota yang berlaku,
  sehingga penugasan sesudah absen mengubah kategori hari itu tanpa menyentuh data absen.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0028_attendance_checkout_city"
down_revision: str | None = "0027_plan_revision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_TRIGGER = """
CREATE OR REPLACE FUNCTION vms.tg_attendance_checkout() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
DECLARE
  v_org  vms.organization%ROWTYPE;
  v_site vms.site%ROWTYPE;
BEGIN
  IF NEW.check_out_at IS NOT NULL AND OLD.check_out_at IS NULL THEN
    SELECT * INTO v_org FROM vms.organization WHERE id = NEW.organization_id;
    NEW.is_early_leave := (NEW.check_out_at AT TIME ZONE v_org.timezone)::time < v_org.shift_end;
    IF NEW.check_out_location IS NOT NULL THEN
      SELECT * INTO v_site FROM vms.site WHERE id = NEW.site_id AND organization_id = NEW.organization_id;
      IF v_site.id IS NOT NULL THEN
        -- Jarak dihitung ulang dari koordinat; nilai kiriman perangkat diabaikan.
        NEW.check_out_distance_m := round(ST_Distance(NEW.check_out_location, v_site.location)::numeric, 1);
        NEW.check_out_outside := NEW.check_out_distance_m > NEW.radius_m;
      END IF;
      IF NEW.check_out_outside THEN
        IF COALESCE(current_setting('app.relax_checkout', true), '') <> 'on' AND NEW.source IN ('MOBILE','WEB') THEN
          IF NEW.check_out_selfie_file_id IS NULL THEN
            RAISE EXCEPTION 'Pulang di luar radius toleransi (% m > % m): swafoto wajib dilampirkan.',
              NEW.check_out_distance_m, NEW.radius_m USING ERRCODE = '23514';
          END IF;
          IF NEW.check_out_explanation IS NULL OR btrim(NEW.check_out_explanation) = '' THEN
            RAISE EXCEPTION 'Pulang di luar radius toleransi (% m > % m): isi penjelasan.',
              NEW.check_out_distance_m, NEW.radius_m USING ERRCODE = '23514';
          END IF;
        END IF;
        IF NEW.status = 'AUTO_VALID' THEN
          NEW.status := 'NEEDS_REVIEW';
        END IF;
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$
"""

_OLD_TRIGGER = """
CREATE OR REPLACE FUNCTION vms.tg_attendance_checkout() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE v_org vms.organization%ROWTYPE;
BEGIN
  IF NEW.check_out_at IS NOT NULL AND OLD.check_out_at IS NULL THEN
    SELECT * INTO v_org FROM vms.organization WHERE id = NEW.organization_id;
    NEW.is_early_leave := (NEW.check_out_at AT TIME ZONE v_org.timezone)::time < v_org.shift_end;
  END IF;
  RETURN NEW;
END $$
"""

_CITY = """
CREATE OR REPLACE FUNCTION vms.attendance_city_category(p_employee uuid, p_date date) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
  SELECT CASE WHEN EXISTS (
    SELECT 1
    FROM vms.work_plan wp
    JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND m.employee_id = p_employee
    WHERE wp.organization_id = vms.current_org_id()
      AND wp.is_out_of_town
      AND wp.status IN ('ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW','COMPLETED')
      AND wp.period @> p_date
      AND m.valid_period @> p_date
  ) THEN 'LUAR_KOTA' ELSE 'DALAM_KOTA' END
$$
"""


def upgrade() -> None:
    op.execute("ALTER TABLE vms.attendance ADD COLUMN IF NOT EXISTS check_out_location geography(Point,4326)")
    op.execute("ALTER TABLE vms.attendance ADD COLUMN IF NOT EXISTS check_out_distance_m numeric(8,1)")
    op.execute("ALTER TABLE vms.attendance ADD COLUMN IF NOT EXISTS check_out_selfie_file_id uuid "
               "REFERENCES vms.file_object(id)")
    op.execute("ALTER TABLE vms.attendance ADD COLUMN IF NOT EXISTS check_out_explanation text")
    op.execute("ALTER TABLE vms.attendance ADD COLUMN IF NOT EXISTS check_out_outside boolean NOT NULL DEFAULT false")
    op.execute(_NEW_TRIGGER)
    op.execute(_CITY)
    op.execute("GRANT EXECUTE ON FUNCTION vms.attendance_city_category(uuid, date) TO vms_api")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS vms.attendance_city_category(uuid, date)")
    op.execute(_OLD_TRIGGER)
    for column in ("check_out_outside", "check_out_explanation", "check_out_selfie_file_id",
                   "check_out_distance_m", "check_out_location"):
        op.execute(f"ALTER TABLE vms.attendance DROP COLUMN IF EXISTS {column}")
