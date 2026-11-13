"""Penerima eksternal peminjaman aset (expand-only, ADR 0003): master penerima + kolom di asset_assignment.

Revision ID: v2_0043
Revises: v2_0042
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0043"
down_revision: str | None = "v2_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = (
    (
        "ix_asset_ext_borrower_office_nama",
        "asset_external_borrowers (office_id, lower(nama)) WHERE delete_at IS NULL",
    ),
    (
        "ix_asset_assignment_ext_borrower",
        "asset_assignment (external_borrower_id) WHERE external_borrower_id IS NOT NULL",
    ),
    (
        "ix_asset_assignment_handover_file",
        "asset_assignment (handover_file_id) WHERE handover_file_id IS NOT NULL",
    ),
    (
        "ix_asset_assignment_due_open",
        "asset_assignment (due_date) WHERE returned_at IS NULL AND delete_at IS NULL AND due_date IS NOT NULL",
    ),
)


def _drop_invalid() -> None:
    names = [n for n, _ in _INDEXES]
    rows = op.get_bind().execute(
        sa.text(
            "SELECT c.relname FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid "
            "WHERE NOT x.indisvalid AND c.relname = ANY(:n)"
        ),
        {"n": names},
    )
    for (name,) in rows.fetchall():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_external_borrowers (
            borrower_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            nama VARCHAR(150) NOT NULL,
            instansi VARCHAR(150) NULL,
            kontak VARCHAR(100) NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delete_at TIMESTAMPTZ NULL,
            CONSTRAINT ck_asset_ext_borrower_nama CHECK (length(btrim(nama)) > 0)
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                GRANT SELECT, INSERT, UPDATE ON asset_external_borrowers TO vms_api;
            END IF;
        END $$
        """
    )
    op.execute("ALTER TABLE asset_assignment ALTER COLUMN employee_id DROP NOT NULL")
    op.execute(
        "ALTER TABLE asset_assignment "
        "ADD COLUMN IF NOT EXISTS external_borrower_id UUID NULL "
        "REFERENCES asset_external_borrowers(borrower_id), "
        "ADD COLUMN IF NOT EXISTS due_date DATE NULL, "
        "ADD COLUMN IF NOT EXISTS handover_file_id UUID NULL REFERENCES file_object(id) ON DELETE SET NULL"
    )
    op.execute("ALTER TABLE asset_assignment DROP CONSTRAINT IF EXISTS ck_assignment_one_borrower")
    op.execute(
        "ALTER TABLE asset_assignment ADD CONSTRAINT ck_assignment_one_borrower "
        "CHECK (num_nonnulls(employee_id, external_borrower_id) = 1) NOT VALID"
    )
    op.execute("ALTER TABLE asset_assignment VALIDATE CONSTRAINT ck_assignment_one_borrower")
    with op.get_context().autocommit_block():
        _drop_invalid()
        for name, target in _INDEXES:
            op.execute(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _ in _INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
    op.execute("ALTER TABLE asset_assignment DROP CONSTRAINT IF EXISTS ck_assignment_one_borrower")
    op.execute(
        "ALTER TABLE asset_assignment DROP COLUMN IF EXISTS handover_file_id, "
        "DROP COLUMN IF EXISTS due_date, DROP COLUMN IF EXISTS external_borrower_id"
    )
    # Gagal keras bila masih ada baris tanpa karyawan (data eksternal sudah hilang di atas).
    op.execute("ALTER TABLE asset_assignment ALTER COLUMN employee_id SET NOT NULL")
    op.execute("DROP TABLE IF EXISTS asset_external_borrowers")
