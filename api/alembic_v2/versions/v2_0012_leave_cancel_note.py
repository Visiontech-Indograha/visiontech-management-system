"""Pembatalan cuti (F7): kolom `leave_request.cancel_note` menyimpan alasan pembatalan.

Idempoten: db/08 sudah memuat kolom ini untuk pemasangan baru.

Revision ID: v2_0012
Revises: v2_0011
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0012"
down_revision: str | None = "v2_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE leave_request ADD COLUMN IF NOT EXISTS cancel_note text NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE leave_request DROP COLUMN IF EXISTS cancel_note")
