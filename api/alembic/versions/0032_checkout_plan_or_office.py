"""Absen pulang sah di lokasi absen masuk, kantor, atau lokasi rencana kerja hari itu (permintaan pemilik 2026-10-09).

Revision ID: 0032_checkout_plan_or_office
Revises: 0031_plan_day_site_members
Create Date: 2026-10-09

Contoh: karyawan absen masuk di kantor, pukul 10 baru mendapat rencana kerja di lokasi lain. Pulang di lokasi rencana
(hari itu) maupun di kantor tidak lagi dianggap di luar radius. Jarak dihitung ulang di server terhadap lokasi terdekat
yang sah: (1) lokasi absen masuk, (2) lokasi kantor (`site.unit_id IS NULL`), (3) lokasi hari ini dari rencana kerja
berjalan yang menugaskan karyawan itu (lokasi khusus hari itu atau lokasi rencana). Di luar semuanya: aturan lama
(swafoto + penjelasan wajib, status Perlu review).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0032_checkout_plan_or_office"
down_revision: str | None = "0031_plan_day_site_members"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = """
CREATE OR REPLACE FUNCTION vms.tg_attendance_checkout() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
DECLARE
  v_org    vms.organization%ROWTYPE;
  v_dist   numeric;
  v_radius integer;
BEGIN
  IF NEW.check_out_at IS NOT NULL AND OLD.check_out_at IS NULL THEN
    SELECT * INTO v_org FROM vms.organization WHERE id = NEW.organization_id;
    NEW.is_early_leave := (NEW.check_out_at AT TIME ZONE v_org.timezone)::time < v_org.shift_end;
    IF NEW.check_out_location IS NOT NULL THEN
      -- Jarak dihitung ulang dari koordinat (nilai perangkat diabaikan) ke lokasi sah TERDEKAT: lokasi absen masuk,
      -- kantor, atau lokasi hari ini dari rencana kerja berjalan yang menugaskan karyawan ini.
      SELECT c.dist, c.radius INTO v_dist, v_radius
      FROM (
        SELECT ST_Distance(NEW.check_out_location, s.location)::numeric AS dist,
               CASE WHEN s.id = NEW.site_id THEN NEW.radius_m ELSE COALESCE(s.radius_m, NEW.radius_m) END AS radius
        FROM vms.site s
        WHERE s.organization_id = NEW.organization_id
          AND (s.id = NEW.site_id
               OR (s.deleted_at IS NULL AND s.unit_id IS NULL)
               OR (s.deleted_at IS NULL AND s.id IN (
                     SELECT COALESCE(d.site_id, wp.site_id)
                     FROM vms.work_plan wp
                     JOIN vms.work_plan_day d ON d.work_plan_id = wp.id
                     JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND m.employee_id = NEW.employee_id
                     WHERE wp.organization_id = NEW.organization_id
                       AND wp.status = 'IN_PROGRESS'
                       AND d.work_date = (NEW.check_out_at AT TIME ZONE v_org.timezone)::date
                       AND m.valid_period @> d.work_date
                       AND (NOT EXISTS (SELECT 1 FROM vms.work_plan_day_member dm WHERE dm.work_plan_day_id = d.id)
                            OR EXISTS (SELECT 1 FROM vms.work_plan_day_member dm
                                       WHERE dm.work_plan_day_id = d.id AND dm.employee_id = NEW.employee_id)))))
      ) c
      ORDER BY (c.dist - c.radius)
      LIMIT 1;
      IF v_dist IS NOT NULL THEN
        NEW.check_out_distance_m := round(v_dist, 1);
        NEW.check_out_outside := v_dist > v_radius;
      END IF;
      IF NEW.check_out_outside THEN
        IF COALESCE(current_setting('app.relax_checkout', true), '') <> 'on' AND NEW.source IN ('MOBILE','WEB') THEN
          IF NEW.check_out_selfie_file_id IS NULL THEN
            RAISE EXCEPTION 'Pulang di luar radius toleransi (% m > % m): swafoto wajib dilampirkan.',
              NEW.check_out_distance_m, v_radius USING ERRCODE = '23514';
          END IF;
          IF NEW.check_out_explanation IS NULL OR btrim(NEW.check_out_explanation) = '' THEN
            RAISE EXCEPTION 'Pulang di luar radius toleransi (% m > % m): isi penjelasan.',
              NEW.check_out_distance_m, v_radius USING ERRCODE = '23514';
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

_OLD = """
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


def upgrade() -> None:
    op.execute(_NEW)


def downgrade() -> None:
    op.execute(_OLD)
