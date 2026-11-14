"""Alasan tolak inspeksi kendaraan terpisah dari catatan pemeriksa (expand-only).

Revision ID: v2_0045
Revises: v2_0044
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0045"
down_revision: str | None = "v2_0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vehicle_safety_inspections ADD COLUMN IF NOT EXISTS reject_reason TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE vehicle_safety_inspections DROP COLUMN IF EXISTS reject_reason")
