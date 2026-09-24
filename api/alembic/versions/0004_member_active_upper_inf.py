"""keanggotaan aktif = valid_period tak berbatas atas dan tidak kosong (R3)

Adendum personel menutup baris ketua lama dengan `daterange(lower, CURRENT_DATE, '[)')`. Bila
baris itu dibuka hari yang sama, hasilnya rentang **kosong** — dan `upper('empty') IS NULL`
bernilai benar, sehingga ketua lama tetap terhitung anggota aktif. `upper_inf()` bernilai salah
untuk rentang kosong. Berlaku untuk `is_plan_member` dan `personnel_conflict`.

Revision ID: 0004_member_active_upper_inf
Revises: 0003_face_after_geofence
Create Date: 2026-09-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004_member_active_upper_inf"
down_revision: str | Sequence[str] | None = "0003_face_after_geofence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_IS_PLAN_MEMBER = """
CREATE OR REPLACE FUNCTION vms.is_plan_member(p_plan uuid, p_user uuid DEFAULT vms.current_user_id()) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM work_plan_member m
    JOIN app_user u ON u.employee_id = m.employee_id
    WHERE m.work_plan_id = p_plan AND u.id = p_user AND {active}
  )
$$;
"""

_PERSONNEL_CONFLICT = """
CREATE OR REPLACE FUNCTION vms.personnel_conflict(p_employee uuid, p_period daterange, p_exclude_plan uuid DEFAULT NULL)
RETURNS TABLE (work_plan_id uuid, number text, title text)
LANGUAGE sql STABLE AS $$
  SELECT wp.id, wp.number, wp.title
  FROM work_plan wp
  JOIN work_plan_member m ON m.work_plan_id = wp.id AND {active}
  WHERE m.employee_id = p_employee
    AND wp.deleted_at IS NULL
    AND wp.status IN ('PUBLISHED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW')
    AND (p_exclude_plan IS NULL OR wp.id <> p_exclude_plan)
    AND wp.period && p_period
$$;
"""


def _apply(active: str) -> None:
    # Badan fungsi memakai nama tabel tanpa skema (search_path = vms, public) — sama dengan db/02.
    op.execute("SET LOCAL search_path = vms, public")
    op.execute(_IS_PLAN_MEMBER.format(active=active))
    op.execute(_PERSONNEL_CONFLICT.format(active=active))


def upgrade() -> None:
    _apply("upper_inf(m.valid_period)")


def downgrade() -> None:
    _apply("upper(m.valid_period) IS NULL")
