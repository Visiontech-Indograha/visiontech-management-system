"""Daily report corrections: leader asks, PM approves/returns until accepted.

Revision ID: v2_0006
Revises: v2_0005
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0006"
down_revision: str | None = "v2_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_report_correction (
            correction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            daily_plan_id UUID NOT NULL REFERENCES work_plan_daily(daily_plan_id),
            requested_by_id UUID NOT NULL REFERENCES employee(employee_id),
            reason TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'REQUESTED'
                CHECK (status IN ('REQUESTED', 'REVISING', 'IN_REVIEW', 'ACCEPTED', 'REJECTED')),
            review_note TEXT NULL,
            reviewed_by_id UUID NULL REFERENCES employee(employee_id),
            reviewed_at TIMESTAMPTZ NULL,
            revision_count INT NOT NULL DEFAULT 0,
            create_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delete_at TIMESTAMPTZ NULL
        )
        """
    )
    # Satu koreksi terbuka per jadwal harian.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_report_correction_open
            ON daily_report_correction (daily_plan_id)
            WHERE status IN ('REQUESTED', 'REVISING', 'IN_REVIEW') AND delete_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS daily_report_correction")
