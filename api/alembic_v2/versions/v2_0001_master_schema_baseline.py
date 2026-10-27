"""Baseline for the existing Master Schema V2 bootstrap.

Revision ID: v2_0001
Revises:

The base schema is installed by db/06_master_schema_v2.sql and
db/08_master_v2_tambahan.sql. This revision records and validates that baseline;
it does not create, drop, or alter application objects.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "v2_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BOOTSTRAP_TABLES = (
    "address",
    "app_activity_logs",
    "asset_assignment",
    "attendance",
    "attendance_site_visit",
    "client",
    "company_mess_stay",
    "division",
    "document_template_export",
    "employee",
    "employee_file",
    "employee_offboarding",
    "file_object",
    "image_requirement",
    "job_position",
    "leave_balance",
    "leave_request",
    "member",
    "offboarding_clearance_item",
    "office",
    "operational_expense",
    "overtime",
    "project",
    "system_backup_registry",
    "team",
    "tool",
    "user_sessions",
    "users",
    "vehicle",
    "vehicle_file",
    "vehicle_inspection",
    "work_completion",
    "work_completion_bom",
    "work_plan_attachment",
    "work_plan_daily",
    "work_plan_item",
    "work_type",
    "work_type_default_materials",
)


def upgrade() -> None:
    if context.is_offline_mode():
        return

    connection = op.get_bind()
    missing = [
        name
        for name in _BOOTSTRAP_TABLES
        if connection.execute(
            sa.text("SELECT to_regclass(:table_name)"),
            {"table_name": f"public.{name}"},
        ).scalar_one_or_none()
        is None
    ]
    if missing:
        raise RuntimeError(
            "Master Schema V2 bootstrap is incomplete; install db/06 and db/08 first. "
            f"Missing tables: {', '.join(missing)}"
        )


def downgrade() -> None:
    raise RuntimeError("The Master Schema V2 baseline cannot be downgraded.")
