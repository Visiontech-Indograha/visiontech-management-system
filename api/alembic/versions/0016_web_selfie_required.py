"""Swafoto wajib di luar radius juga untuk absen web (R-33, keputusan pemilik 2026-10-02).

Trigger `tg_attendance_geofence` sebelumnya hanya mewajibkan swafoto untuk sumber MOBILE.

Revision ID: 0016_web_selfie_required
Revises: 0015_attendance_scope_functions
Create Date: 2026-10-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0016_web_selfie_required"
down_revision: str | Sequence[str] | None = "0015_attendance_scope_functions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW = "CREATE OR REPLACE FUNCTION tg_attendance_geofence() RETURNS trigger\nLANGUAGE plpgsql AS $$\nDECLARE\n  v_site   site%ROWTYPE;\n  v_org    organization%ROWTYPE;\n  v_radius integer;\nBEGIN\n  SELECT * INTO v_org FROM organization WHERE id = NEW.organization_id;\n  SELECT * INTO v_site FROM site WHERE id = NEW.site_id;\n  v_radius := COALESCE(v_site.radius_m, v_org.geofence_radius_m, 100);\n  NEW.radius_m := v_radius;\n\n  IF NEW.source = 'MACHINE' THEN\n    NEW.distance_m := 0;\n    NEW.location := NULL;\n  ELSIF NEW.location IS NOT NULL AND v_site.id IS NOT NULL THEN\n    -- Jarak dihitung ulang dari koordinat; nilai kiriman perangkat diabaikan.\n    NEW.distance_m := round(ST_Distance(NEW.location, v_site.location)::numeric, 1);\n  END IF;\n\n  NEW.status := CASE WHEN NEW.distance_m > v_radius THEN 'NEEDS_REVIEW'::attendance_status\n                     ELSE 'AUTO_VALID'::attendance_status END;\n\n  -- R-33: swafoto wajib di luar radius untuk absen HP maupun web (mesin absen dikecualikan).\n  IF NEW.status = 'NEEDS_REVIEW' AND NEW.source IN ('MOBILE','WEB') AND NEW.selfie_file_id IS NULL THEN\n    RAISE EXCEPTION 'Di luar radius toleransi (% m > % m): swafoto wajib dilampirkan.', NEW.distance_m, v_radius\n      USING ERRCODE = '23514';\n  END IF;\n\n  NEW.is_late := (NEW.check_in_at AT TIME ZONE v_org.timezone)::time > v_org.shift_start;\n  RETURN NEW;\nEND $$;"

_OLD = "CREATE OR REPLACE FUNCTION tg_attendance_geofence() RETURNS trigger\nLANGUAGE plpgsql AS $$\nDECLARE\n  v_site   site%ROWTYPE;\n  v_org    organization%ROWTYPE;\n  v_radius integer;\nBEGIN\n  SELECT * INTO v_org FROM organization WHERE id = NEW.organization_id;\n  SELECT * INTO v_site FROM site WHERE id = NEW.site_id;\n  v_radius := COALESCE(v_site.radius_m, v_org.geofence_radius_m, 100);\n  NEW.radius_m := v_radius;\n\n  IF NEW.source = 'MACHINE' THEN\n    NEW.distance_m := 0;\n    NEW.location := NULL;\n  ELSIF NEW.location IS NOT NULL AND v_site.id IS NOT NULL THEN\n    -- Jarak dihitung ulang dari koordinat; nilai kiriman perangkat diabaikan.\n    NEW.distance_m := round(ST_Distance(NEW.location, v_site.location)::numeric, 1);\n  END IF;\n\n  NEW.status := CASE WHEN NEW.distance_m > v_radius THEN 'NEEDS_REVIEW'::attendance_status\n                     ELSE 'AUTO_VALID'::attendance_status END;\n\n  IF NEW.status = 'NEEDS_REVIEW' AND NEW.source = 'MOBILE' AND NEW.selfie_file_id IS NULL THEN\n    RAISE EXCEPTION 'Di luar radius toleransi (% m > % m): swafoto wajib dilampirkan.', NEW.distance_m, v_radius\n      USING ERRCODE = '23514';\n  END IF;\n\n  NEW.is_late := (NEW.check_in_at AT TIME ZONE v_org.timezone)::time > v_org.shift_start;\n  RETURN NEW;\nEND $$;"


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(_NEW)


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(_OLD)
