"""Penandatanganan BAST berurutan pada Work Order: ketua tim lebih dulu, lalu PM/OM dalam cakupan.

Expand-only: hanya menambah kolom nullable pada `client_work_orders` untuk tanda tangan ketua tim.
Tanda tangan final (PM/OM) tetap memakai kolom `bast_*` yang sudah ada.

Revision ID: v2_0020
Revises: v2_0019
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0020"
down_revision: str | None = "v2_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE client_work_orders ADD COLUMN IF NOT EXISTS leader_signed_at TIMESTAMPTZ")
    op.execute(
        "ALTER TABLE client_work_orders ADD COLUMN IF NOT EXISTS leader_signed_by UUID "
        "REFERENCES users(user_id) ON DELETE SET NULL"
    )
    op.execute("ALTER TABLE client_work_orders ADD COLUMN IF NOT EXISTS leader_signer_name VARCHAR(120)")
    op.execute(
        "ALTER TABLE client_work_orders ADD COLUMN IF NOT EXISTS leader_signature_file_id UUID "
        "REFERENCES file_object(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE client_work_orders DROP COLUMN IF EXISTS leader_signature_file_id")
    op.execute("ALTER TABLE client_work_orders DROP COLUMN IF EXISTS leader_signer_name")
    op.execute("ALTER TABLE client_work_orders DROP COLUMN IF EXISTS leader_signed_by")
    op.execute("ALTER TABLE client_work_orders DROP COLUMN IF EXISTS leader_signed_at")
