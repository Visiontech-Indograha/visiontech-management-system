"""Asset loan requests (employee asks, HR/GA approves) and return-request columns.

Revision ID: v2_0005
Revises: v2_0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0005"
down_revision: str | None = "v2_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_loan_request (
            request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            asset_type VARCHAR(20) NOT NULL,
            tool_id UUID NULL REFERENCES tool(tool_id),
            vehicle_id UUID NULL REFERENCES vehicle(vehicle_id),
            employee_id UUID NOT NULL REFERENCES employee(employee_id),
            purpose TEXT NOT NULL,
            needed_on DATE NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')),
            review_note TEXT NULL,
            reviewed_by_id UUID NULL REFERENCES employee(employee_id),
            reviewed_at TIMESTAMPTZ NULL,
            assignment_id UUID NULL REFERENCES asset_assignment(assignment_id),
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_asset_loan_request_employee ON asset_loan_request (employee_id, status)"
    )
    for col, ddl in (
        ("return_requested_at", "TIMESTAMPTZ NULL"),
        ("return_condition", "VARCHAR(20) NULL"),
        ("return_note", "TEXT NULL"),
        ("return_photo_path", "VARCHAR(255) NULL"),
    ):
        op.execute(f"ALTER TABLE asset_assignment ADD COLUMN IF NOT EXISTS {col} {ddl}")


def downgrade() -> None:
    for col in ("return_photo_path", "return_note", "return_condition", "return_requested_at"):
        op.execute(f"ALTER TABLE asset_assignment DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS asset_loan_request")
