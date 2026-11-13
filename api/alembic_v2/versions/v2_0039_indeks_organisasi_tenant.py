"""Indeks komposit organisasi/kantor pendukung isolasi tenant RLS (B-08).

Expand-only: hanya menambah indeks komposit CONCURRENTLY untuk mempercepat kueri
berpredikat organisasi/kantor (tenant) pada tabel utama P1 & P2 multi-tenant:
- `attendance`: (office_id, attendance_date DESC) WHERE delete_at IS NULL
- `employee`: (office_id, offboarding_status) WHERE delete_at IS NULL
- `employee`: (office_id, division_id) WHERE delete_at IS NULL
- `operational_expense`: (office_id, expense_date DESC) WHERE delete_at IS NULL
- `project`: (office_id, status) WHERE delete_at IS NULL
- `team`: (office_id, status) WHERE delete_at IS NULL
- `tool`: (office_id, status) WHERE delete_at IS NULL
- `vehicle`: (office_id, status) WHERE delete_at IS NULL
- `idempotency_keys`: (organization_id, created_at DESC)

Revision ID: v2_0039
Revises: v2_0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0039"
down_revision: str | None = "v2_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES: tuple[tuple[str, str], ...] = (
    (
        "ix_attendance_office_date",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_office_date "
        "ON public.attendance (office_id, attendance_date DESC) WHERE delete_at IS NULL",
    ),
    (
        "ix_employee_office_status",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_office_status "
        "ON public.employee (office_id, offboarding_status) WHERE delete_at IS NULL",
    ),
    (
        "ix_employee_office_division",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_employee_office_division "
        "ON public.employee (office_id, division_id) WHERE delete_at IS NULL",
    ),
    (
        "ix_operational_expense_office_date",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_operational_expense_office_date "
        "ON public.operational_expense (office_id, expense_date DESC) WHERE delete_at IS NULL",
    ),
    (
        "ix_project_office_status",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_project_office_status "
        "ON public.project (office_id, status) WHERE delete_at IS NULL",
    ),
    (
        "ix_team_office_status",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_team_office_status "
        "ON public.team (office_id, status) WHERE delete_at IS NULL",
    ),
    (
        "ix_tool_office_status",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tool_office_status "
        "ON public.tool (office_id, status) WHERE delete_at IS NULL",
    ),
    (
        "ix_vehicle_office_status",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_vehicle_office_status "
        "ON public.vehicle (office_id, status) WHERE delete_at IS NULL",
    ),
    (
        "ix_idempotency_keys_org_created",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_idempotency_keys_org_created "
        "ON public.idempotency_keys (organization_id, created_at DESC)",
    ),
)


def _drop_invalid(names: list[str]) -> None:
    """Indeks CONCURRENTLY yang gagal tertinggal INVALID dan akan dilewati oleh IF NOT EXISTS: buang dulu."""
    rows = op.get_bind().execute(
        sa.text(
            "SELECT c.relname FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid "
            "WHERE NOT x.indisvalid AND c.relname = ANY(:n)"
        ),
        {"n": names},
    )
    for (name,) in rows:
        op.execute(f"DROP INDEX IF EXISTS public.{name}")


def upgrade() -> None:
    _drop_invalid([name for name, _ in _INDEXES])
    with op.get_context().autocommit_block():
        for _, sql in _INDEXES:
            op.execute(sql)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _ in reversed(_INDEXES):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
