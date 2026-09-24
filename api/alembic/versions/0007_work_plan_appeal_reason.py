"""alasan banding ketua pada SK (V-20, domain.js APPEAL: plan.appealReason)

Revision ID: 0007_work_plan_appeal_reason
Revises: 0006_audit_org_from_row
Create Date: 2026-09-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0007_work_plan_appeal_reason"
down_revision: str | Sequence[str] | None = "0006_audit_org_from_row"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan ADD COLUMN IF NOT EXISTS appeal_reason text")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan DROP COLUMN IF EXISTS appeal_reason")
