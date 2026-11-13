"""Pengingat dokumen kendaraan (expand-only): jenis dokumen, riwayat dokumen kendaraan, pengemudi, log pengingat.

Revision ID: v2_0041
Revises: v2_0040
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0041"
down_revision: str | None = "v2_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("document_type", "vehicle_document", "vehicle_driver", "document_reminder")

_INDEXES = (
    ("ix_vehicle_document_vehicle", "vehicle_document (vehicle_id, doc_type_code) WHERE delete_at IS NULL"),
    (
        "uq_vehicle_document_active",
        "vehicle_document (vehicle_id, doc_type_code) WHERE status = 'active' AND delete_at IS NULL",
    ),
    (
        "ix_vehicle_document_due",
        "vehicle_document (expired_on, office_id) WHERE status = 'active' AND delete_at IS NULL",
    ),
    ("ix_vehicle_document_type", "vehicle_document (doc_type_code)"),
    ("ix_vehicle_document_file", "vehicle_document (file_object_id) WHERE file_object_id IS NOT NULL"),
    ("ix_vehicle_document_legacy", "vehicle_document (vehicle_file_id) WHERE vehicle_file_id IS NOT NULL"),
    (
        "uq_vehicle_driver_active",
        "vehicle_driver (vehicle_id, employee_id) WHERE selesai_on IS NULL AND delete_at IS NULL",
    ),
    ("ix_vehicle_driver_employee", "vehicle_driver (employee_id) WHERE delete_at IS NULL"),
    ("ix_vehicle_driver_office", "vehicle_driver (office_id) WHERE delete_at IS NULL"),
    ("uq_document_reminder_once", "document_reminder (doc_kind, doc_id, due_date, stage) WHERE stage <> 'DAILY'"),
    ("ix_document_reminder_office_day", "document_reminder (office_id, send_date)"),
    ("ix_document_reminder_doc", "document_reminder (doc_kind, doc_id, send_date DESC)"),
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
        CREATE TABLE IF NOT EXISTS document_type (
            code VARCHAR(30) PRIMARY KEY,
            nama VARCHAR(100) NOT NULL,
            berlaku_untuk TEXT NOT NULL,
            ambang_hari INT[] NOT NULL DEFAULT '{30,21,14}',
            harian_mulai_hari INT NOT NULL DEFAULT 7,
            aktif BOOLEAN NOT NULL DEFAULT TRUE,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_document_type_untuk CHECK (berlaku_untuk IN ('KENDARAAN', 'KARYAWAN')),
            CONSTRAINT ck_document_type_harian CHECK (harian_mulai_hari BETWEEN 0 AND 60),
            CONSTRAINT ck_document_type_ambang CHECK (cardinality(ambang_hari) <= 10)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicle_document (
            vehicle_document_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            vehicle_id UUID NOT NULL REFERENCES vehicle(vehicle_id),
            doc_type_code VARCHAR(30) NOT NULL REFERENCES document_type(code),
            doc_no VARCHAR(100) NULL,
            issued_on DATE NULL,
            expired_on DATE NOT NULL,
            file_object_id UUID NULL REFERENCES file_object(id),
            vehicle_file_id UUID NULL REFERENCES vehicle_file(vehicle_file_id),
            status TEXT NOT NULL DEFAULT 'active',
            catatan TEXT NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delete_at TIMESTAMPTZ NULL,
            CONSTRAINT ck_vehicle_document_status CHECK (status IN ('active', 'replaced')),
            CONSTRAINT ck_vehicle_document_tanggal CHECK (issued_on IS NULL OR issued_on <= expired_on)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicle_driver (
            vehicle_driver_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            vehicle_id UUID NOT NULL REFERENCES vehicle(vehicle_id),
            employee_id UUID NOT NULL REFERENCES employee(employee_id),
            mulai_on DATE NOT NULL DEFAULT CURRENT_DATE,
            selesai_on DATE NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delete_at TIMESTAMPTZ NULL,
            CONSTRAINT ck_vehicle_driver_tanggal CHECK (selesai_on IS NULL OR selesai_on >= mulai_on)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_reminder (
            reminder_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            doc_kind TEXT NOT NULL,
            doc_id UUID NOT NULL,
            due_date DATE NOT NULL,
            stage TEXT NOT NULL,
            send_date DATE NOT NULL,
            jumlah_penerima INT NOT NULL DEFAULT 0,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_document_reminder_kind CHECK (doc_kind IN ('VEHICLE_DOCUMENT', 'EMPLOYEE_FILE')),
            CONSTRAINT ck_document_reminder_stage CHECK (stage IN ('T30', 'T21', 'T14', 'DAILY')),
            CONSTRAINT uq_document_reminder_key UNIQUE (doc_kind, doc_id, due_date, stage, send_date)
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                GRANT SELECT, INSERT, UPDATE ON document_type, vehicle_document, vehicle_driver TO vms_api;
                GRANT SELECT, INSERT ON document_reminder TO vms_api;
            END IF;
        END $$
        """
    )
    with op.get_context().autocommit_block():
        _drop_invalid()
        for name, target in _INDEXES:
            u = "UNIQUE " if name.startswith("uq_") else ""
            op.execute(f"CREATE {u}INDEX CONCURRENTLY IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _ in _INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
    for t in reversed(_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {t}")
