"""Add composite performance indexes for attendance, work plans, and work completion.

Revision ID: v2_0003
Revises: v2_0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0003"
down_revision: str | None = "v2_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    indexes = (
        (
            "idx_attendance_emp_date",
            "CREATE INDEX IF NOT EXISTS idx_attendance_emp_date "
            "ON attendance(employee_id, attendance_date) WHERE delete_at IS NULL",
        ),
        (
            "idx_work_plan_daily_team_date",
            "CREATE INDEX IF NOT EXISTS idx_work_plan_daily_team_date "
            "ON work_plan_daily(team_id, work_date) WHERE delete_at IS NULL",
        ),
        (
            "idx_work_completion_division",
            "CREATE INDEX IF NOT EXISTS idx_work_completion_division "
            "ON work_completion(division_id) WHERE delete_at IS NULL",
        ),
    )
    for _, sql in indexes:
        op.execute(sql)


def downgrade() -> None:
    for name in (
        "idx_attendance_emp_date",
        "idx_work_plan_daily_team_date",
        "idx_work_completion_division",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
