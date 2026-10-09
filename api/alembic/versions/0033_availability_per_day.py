"""Ketersediaan karyawan per hari kerja (permintaan pemilik 2026-10-09, mengikuti 0031).

Revision ID: 0033_availability_per_day
Revises: 0032_checkout_plan_or_office
Create Date: 2026-10-09

Sebelumnya bentrok jadwal dihitung per periode rencana: anggota yang tidak bertugas pada hari tertentu tetap dianggap
sibuk. Sekarang yang dihitung adalah HARI BERTUGAS: seseorang bertugas pada sebuah hari rencana bila ia anggota/ketua
rencana itu DAN (hari itu tanpa daftar anggota khusus ATAU ia ada di daftar). Dua rencana bentrok hanya bila ada tanggal
yang sama di mana ia bertugas di keduanya.

- `personnel_conflict(p_employee, p_period, p_exclude_plan)`: rencana aktif lain yang punya hari bertugas karyawan itu
  dalam `p_period`; bila `p_exclude_plan` (rencana kandidat) punya hari kerja, hanya tanggal yang sama yang dihitung.
- `employee_busy_dates(p_employee, p_exclude_plan)`: tanggal (hari ini dan sesudahnya) di mana karyawan bertugas pada
  rencana aktif lain; dipakai form untuk memberi tahu PM kapan karyawan sibuk.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0033_availability_per_day"
down_revision: str | None = "0032_checkout_plan_or_office"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ON_DUTY = """
    (NOT EXISTS (SELECT 1 FROM vms.work_plan_day_member dm WHERE dm.work_plan_day_id = {day}.id)
     OR EXISTS (SELECT 1 FROM vms.work_plan_day_member dm
                WHERE dm.work_plan_day_id = {day}.id AND dm.employee_id = p_employee))
"""

_NEW_CONFLICT = f"""
CREATE OR REPLACE FUNCTION vms.personnel_conflict(p_employee uuid, p_period daterange, p_exclude_plan uuid DEFAULT NULL)
RETURNS TABLE (work_plan_id uuid, number text, title text)
LANGUAGE sql STABLE AS $$
  SELECT DISTINCT wp.id, wp.number, wp.title
  FROM vms.work_plan wp
  JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND upper_inf(m.valid_period)
  JOIN vms.work_plan_day d ON d.work_plan_id = wp.id
  WHERE m.employee_id = p_employee
    AND wp.deleted_at IS NULL
    AND wp.status IN ('PUBLISHED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
    AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
    AND p_period @> d.work_date
    AND {_ON_DUTY.format(day='d')}
    AND (p_exclude_plan IS NULL
         OR NOT EXISTS (SELECT 1 FROM vms.work_plan_day c WHERE c.work_plan_id = p_exclude_plan)
         OR EXISTS (SELECT 1 FROM vms.work_plan_day c
                    WHERE c.work_plan_id = p_exclude_plan AND c.work_date = d.work_date
                      AND {_ON_DUTY.format(day='c')}))
$$
"""

_OLD_CONFLICT = """
CREATE OR REPLACE FUNCTION vms.personnel_conflict(p_employee uuid, p_period daterange, p_exclude_plan uuid DEFAULT NULL)
RETURNS TABLE (work_plan_id uuid, number text, title text)
LANGUAGE sql STABLE AS $$
  SELECT wp.id, wp.number, wp.title
  FROM vms.work_plan wp
  JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND upper_inf(m.valid_period)
  WHERE m.employee_id = p_employee
    AND wp.deleted_at IS NULL
    AND wp.status IN ('PUBLISHED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
    AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
    AND wp.period && p_period
$$
"""

_BUSY = f"""
CREATE OR REPLACE FUNCTION vms.employee_busy_dates(p_employee uuid, p_exclude_plan uuid DEFAULT NULL)
RETURNS TABLE (busy_date date)
LANGUAGE sql STABLE AS $$
  SELECT DISTINCT d.work_date
  FROM vms.work_plan wp
  JOIN vms.work_plan_member m ON m.work_plan_id = wp.id AND upper_inf(m.valid_period)
  JOIN vms.work_plan_day d ON d.work_plan_id = wp.id
  JOIN vms.organization o ON o.id = wp.organization_id
  WHERE m.employee_id = p_employee
    AND wp.deleted_at IS NULL
    AND wp.status IN ('PUBLISHED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
    AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
    AND d.work_date >= (now() AT TIME ZONE o.timezone)::date
    AND {_ON_DUTY.format(day='d')}
  ORDER BY d.work_date
$$
"""


def upgrade() -> None:
    op.execute(_NEW_CONFLICT)
    op.execute(_BUSY)
    op.execute("GRANT EXECUTE ON FUNCTION vms.employee_busy_dates(uuid, uuid) TO vms_api")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS vms.employee_busy_dates(uuid, uuid)")
    op.execute(_OLD_CONFLICT)
