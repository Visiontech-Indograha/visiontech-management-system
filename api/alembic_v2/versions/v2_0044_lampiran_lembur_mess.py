"""Lampiran pengajuan lembur dan mess (expand-only): overtime_attachment, mess_stay_attachment.

Revision ID: v2_0044
Revises: v2_0043
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0044"
down_revision: str | None = "v2_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("overtime_attachment", "mess_stay_attachment")

_INDEXES = (
    ("ix_overtime_attachment_file", "overtime_attachment (file_object_id)"),
    ("ix_overtime_attachment_office", "overtime_attachment (office_id)"),
    ("ix_mess_stay_attachment_file", "mess_stay_attachment (file_object_id)"),
    ("ix_mess_stay_attachment_office", "mess_stay_attachment (office_id)"),
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
    # file_object_id sengaja tanpa ON DELETE CASCADE: berkas yang masih terlampir tidak ikut terhapus oleh
    # pembersih berkas yatim (core/file_cleanup.release_keys_now menangkap IntegrityError).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS overtime_attachment (
            attachment_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            overtime_id UUID NOT NULL REFERENCES overtime(overtime_id) ON DELETE CASCADE,
            file_object_id UUID NOT NULL REFERENCES file_object(id),
            added_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_overtime_attachment UNIQUE (overtime_id, file_object_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mess_stay_attachment (
            attachment_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            mess_stay_id UUID NOT NULL REFERENCES company_mess_stay(mess_stay_id) ON DELETE CASCADE,
            file_object_id UUID NOT NULL REFERENCES file_object(id),
            added_by_user_id UUID NULL REFERENCES users(user_id) ON DELETE SET NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_mess_stay_attachment UNIQUE (mess_stay_id, file_object_id)
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON overtime_attachment, mess_stay_attachment TO vms_api;
            END IF;
        END $$
        """
    )
    with op.get_context().autocommit_block():
        _drop_invalid()
        for name, target in _INDEXES:
            op.execute(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _ in _INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
    for t in reversed(_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {t}")
