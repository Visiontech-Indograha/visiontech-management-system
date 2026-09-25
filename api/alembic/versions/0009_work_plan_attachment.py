"""lampiran draf SK (V-29, domain.js SAVE_ATTACHMENTS; dibekukan di snapshot saat terbit)

Revision ID: 0009_work_plan_attachment
Revises: 0008_work_plan_archive_fields
Create Date: 2026-09-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0009_work_plan_attachment"
down_revision: str | Sequence[str] | None = "0008_work_plan_archive_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vms.work_plan_attachment (
          work_plan_id uuid NOT NULL REFERENCES vms.work_plan(id) ON DELETE CASCADE,
          file_id      uuid NOT NULL REFERENCES vms.file_object(id),
          sort_order   integer NOT NULL DEFAULT 0,
          PRIMARY KEY (work_plan_id, file_id)
        )
        """
    )
    # db/03 memberi hak pada tabel yang sudah ada saat itu; tabel baru perlu hak eksplisit.
    # DELETE diperlukan karena lampiran draf diganti seluruhnya.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON vms.work_plan_attachment TO vms_app;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_readonly') THEN
            GRANT SELECT ON vms.work_plan_attachment TO vms_readonly;
          END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vms.work_plan_attachment")
