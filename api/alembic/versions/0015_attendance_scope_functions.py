"""Cakupan absensi R-33 sebagai fungsi SQL — satu sumber aturan untuk daftar, rekap, swafoto, dan tinjau.

- `attendance_pm_subordinate(viewer, employee)`: viewer PM dan employee pekerja lapangan di unitnya.
- `attendance_is_finance(employee)`: akun karyawan itu berperan FINANCE.
- `attendance_viewable(viewer, view_all, employee)`: milik sendiri, `view_all` (Finance/OPS), atau bawahan PM.
- `attendance_can_review(viewer, employee)`: tidak pernah milik sendiri; PM → bawahan lapangan;
  Finance → pekerja kantor selain Finance; OPS → Finance.

Revision ID: 0015_attendance_scope_functions
Revises: 0014_site_unit
Create Date: 2026-10-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0015_attendance_scope_functions"
down_revision: str | Sequence[str] | None = "0014_site_unit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCTIONS = """
CREATE OR REPLACE FUNCTION attendance_pm_subordinate(p_viewer uuid, p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM vms.employee te
    JOIN vms.user_role pr ON pr.user_id = p_viewer AND pr.role = 'PM'
    WHERE te.id = p_employee AND te.attendance_mode = 'FIELD'
      AND pr.unit_id IS NOT NULL AND pr.unit_id = te.unit_id)
$$;

CREATE OR REPLACE FUNCTION attendance_is_finance(p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM vms.app_user tu JOIN vms.user_role tr ON tr.user_id = tu.id
    WHERE tu.employee_id = p_employee AND tr.role = 'FINANCE')
$$;

CREATE OR REPLACE FUNCTION attendance_viewable(p_viewer uuid, p_view_all boolean, p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT p_view_all
      OR p_employee = (SELECT employee_id FROM vms.app_user WHERE id = p_viewer)
      OR vms.attendance_pm_subordinate(p_viewer, p_employee)
$$;

CREATE OR REPLACE FUNCTION attendance_can_review(p_viewer uuid, p_employee uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT p_employee IS DISTINCT FROM (SELECT employee_id FROM vms.app_user WHERE id = p_viewer)
     AND (vms.attendance_pm_subordinate(p_viewer, p_employee)
          OR (EXISTS (SELECT 1 FROM vms.user_role r WHERE r.user_id = p_viewer AND r.role = 'FINANCE')
              AND EXISTS (SELECT 1 FROM vms.employee te WHERE te.id = p_employee AND te.attendance_mode = 'OFFICE')
              AND NOT vms.attendance_is_finance(p_employee))
          OR (EXISTS (SELECT 1 FROM vms.user_role r WHERE r.user_id = p_viewer AND r.role = 'OPS')
              AND vms.attendance_is_finance(p_employee)))
$$;
"""


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    # asyncpg menolak beberapa perintah dalam satu eksekusi — satu fungsi per eksekusi.
    for statement in FUNCTIONS.split("$$;"):
        if statement.strip():
            op.execute(statement.strip() + "$$;")


def downgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("DROP FUNCTION IF EXISTS attendance_can_review(uuid, uuid)")
    op.execute("DROP FUNCTION IF EXISTS attendance_viewable(uuid, boolean, uuid)")
    op.execute("DROP FUNCTION IF EXISTS attendance_is_finance(uuid)")
    op.execute("DROP FUNCTION IF EXISTS attendance_pm_subordinate(uuid, uuid)")
