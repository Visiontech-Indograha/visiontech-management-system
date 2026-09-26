"""PM memvalidasi absensi karyawan di unitnya (revisi pemilik R-10): kebijakan RLS absensi diperluas

Revision ID: 0010_attendance_pm_unit
Revises: 0009_work_plan_attachment
Create Date: 2026-09-26
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0010_attendance_pm_unit"
down_revision: str | Sequence[str] | None = "0009_work_plan_attachment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS attendance_visibility ON vms.attendance")
    op.execute(
        """
        CREATE POLICY attendance_visibility ON vms.attendance
        USING (
          organization_id = vms.current_org_id() AND (
            vms.has_role('FINANCE') OR vms.has_role('HR') OR vms.has_role('OPS') OR vms.has_role('ADMIN')
            OR employee_id = (SELECT employee_id FROM vms.app_user WHERE id = vms.current_user_id())
            OR EXISTS (SELECT 1 FROM vms.employee e
                       JOIN vms.user_role ur ON ur.user_id = vms.current_user_id() AND ur.role = 'PM'
                       WHERE e.id = attendance.employee_id
                         AND (ur.unit_id IS NULL OR ur.unit_id = e.unit_id))
          )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS attendance_visibility ON vms.attendance")
    op.execute(
        """
        CREATE POLICY attendance_visibility ON vms.attendance
        USING (
          organization_id = vms.current_org_id() AND (
            vms.has_role('FINANCE') OR vms.has_role('HR') OR vms.has_role('OPS') OR vms.has_role('ADMIN')
            OR employee_id = (SELECT employee_id FROM vms.app_user WHERE id = vms.current_user_id())
          )
        )
        """
    )
