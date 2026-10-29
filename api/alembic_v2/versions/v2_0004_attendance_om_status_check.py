"""Constrain attendance.om_approval_status to the values the API writes.

Revision ID: v2_0004
Revises: v2_0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0004"
down_revision: str | None = "v2_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VALUES = "'AUTO_VALID', 'PENDING_OM', 'APPROVED_BY_OM', 'REJECTED_BY_OM', 'APPROVED', 'REJECTED'"


def upgrade() -> None:
    # NOT VALID: baris lama tidak diperiksa ulang (tanpa kunci tabel panjang), baris baru wajib patuh.
    op.execute(
        f"""
        DO $$ BEGIN
            ALTER TABLE attendance ADD CONSTRAINT ck_attendance_om_approval_status
                CHECK (om_approval_status IN ({_VALUES})) NOT VALID;
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS ck_attendance_om_approval_status")
