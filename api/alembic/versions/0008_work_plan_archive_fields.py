"""arsip draf SK: siapa & mengapa (V-21, domain.js DELETE_PLAN: deletedBy, deletionReason)

Revision ID: 0008_work_plan_archive_fields
Revises: 0007_work_plan_appeal_reason
Create Date: 2026-09-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008_work_plan_archive_fields"
down_revision: str | Sequence[str] | None = "0007_work_plan_appeal_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan ADD COLUMN IF NOT EXISTS deleted_by uuid REFERENCES vms.app_user(id)")
    op.execute("ALTER TABLE vms.work_plan ADD COLUMN IF NOT EXISTS deletion_reason text")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.work_plan DROP COLUMN IF EXISTS deletion_reason")
    op.execute("ALTER TABLE vms.work_plan DROP COLUMN IF EXISTS deleted_by")
