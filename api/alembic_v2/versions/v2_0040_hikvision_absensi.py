"""Absensi Hikvision (expand-only): perangkat, event mentah, pemetaan karyawan, kolom sumber attendance.

Revision ID: v2_0040
Revises: v2_0039
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0040"
down_revision: str | None = "v2_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = (
    ("uq_hikvision_device_serial_active", "hikvision_device (serial_no) WHERE delete_at IS NULL", True),
    ("ix_hikvision_device_office", "hikvision_device (office_id) WHERE delete_at IS NULL", False),
    ("ix_hikvision_event_device_time", "hikvision_event (device_id, event_time DESC)", False),
    ("ix_hikvision_event_employee_no", "hikvision_event (device_id, employee_no_string, event_time DESC)", False),
    ("ix_hikvision_event_unprocessed", "hikvision_event (received_at) WHERE diproses_at IS NULL", False),
    ("ix_hikvision_event_employee", "hikvision_event (employee_id) WHERE employee_id IS NOT NULL", False),
    ("uq_hikvision_event_device_key", "hikvision_event (device_id, event_key) WHERE event_key IS NOT NULL", True),
    (
        "uq_hikvision_map_device_no_active",
        "hikvision_employee_map (device_id, employee_no_string) WHERE delete_at IS NULL",
        True,
    ),
    ("ix_hikvision_map_employee", "hikvision_employee_map (employee_id) WHERE delete_at IS NULL", False),
    ("ix_attendance_device_event", "attendance (device_event_id) WHERE device_event_id IS NOT NULL", False),
)


def _drop_invalid() -> None:
    names = [n for n, _, _ in _INDEXES]
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
        CREATE TABLE IF NOT EXISTS hikvision_device (
            device_id UUID PRIMARY KEY DEFAULT uuidv7(),
            office_id UUID NOT NULL REFERENCES office(office_id),
            name VARCHAR(100) NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            http_port INT NOT NULL DEFAULT 80,
            serial_no VARCHAR(64) NOT NULL,
            model VARCHAR(64) NULL,
            token_hash CHAR(64) NOT NULL,
            aktif BOOLEAN NOT NULL DEFAULT TRUE,
            mode VARCHAR(10) NOT NULL DEFAULT 'SHADOW',
            catatan TEXT NULL,
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delete_at TIMESTAMPTZ NULL,
            CONSTRAINT ck_hikvision_device_mode CHECK (mode IN ('SHADOW', 'AKTIF')),
            CONSTRAINT ck_hikvision_device_port CHECK (http_port BETWEEN 1 AND 65535),
            CONSTRAINT uq_hikvision_device_token_hash UNIQUE (token_hash)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hikvision_event (
            event_id UUID PRIMARY KEY DEFAULT uuidv7(),
            device_id UUID NOT NULL REFERENCES hikvision_device(device_id),
            serial_no_event INT NULL,
            event_key CHAR(64) NULL,
            major_event_type INT NOT NULL,
            minor_event_type INT NOT NULL,
            event_time TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            employee_no_string VARCHAR(50) NULL,
            card_no VARCHAR(50) NULL,
            verify_mode VARCHAR(40) NULL,
            picture_path VARCHAR(255) NULL,
            payload JSONB NOT NULL,
            sumber VARCHAR(4) NOT NULL,
            employee_id UUID NULL REFERENCES employee(employee_id),
            diproses_at TIMESTAMPTZ NULL,
            CONSTRAINT uq_hikvision_event_device_serial UNIQUE (device_id, serial_no_event),
            CONSTRAINT ck_hikvision_event_sumber CHECK (sumber IN ('PUSH', 'PULL')),
            CONSTRAINT ck_hikvision_event_kunci CHECK (serial_no_event IS NOT NULL OR event_key IS NOT NULL)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hikvision_employee_map (
            map_id UUID PRIMARY KEY DEFAULT uuidv7(),
            device_id UUID NOT NULL REFERENCES hikvision_device(device_id),
            employee_no_string VARCHAR(50) NOT NULL,
            employee_id UUID NOT NULL REFERENCES employee(employee_id),
            create_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            delete_at TIMESTAMPTZ NULL
        )
        """
    )
    op.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS source TEXT NULL")
    op.execute(
        "ALTER TABLE attendance ADD COLUMN IF NOT EXISTS device_event_id UUID NULL "
        "REFERENCES hikvision_event(event_id)"
    )
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS ck_attendance_source")
    op.execute(
        "ALTER TABLE attendance ADD CONSTRAINT ck_attendance_source "
        "CHECK (source IS NULL OR source IN ('APP_HP', 'WEB', 'HIKVISION')) NOT VALID"
    )
    op.execute("ALTER TABLE attendance VALIDATE CONSTRAINT ck_attendance_source")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                GRANT SELECT, INSERT, UPDATE ON hikvision_device, hikvision_event, hikvision_employee_map TO vms_api;
            END IF;
        END $$
        """
    )
    with op.get_context().autocommit_block():
        _drop_invalid()
        for name, target, unique in _INDEXES:
            u = "UNIQUE " if unique else ""
            op.execute(f"CREATE {u}INDEX CONCURRENTLY IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, _, _ in _INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")
    op.execute("ALTER TABLE attendance DROP CONSTRAINT IF EXISTS ck_attendance_source")
    op.execute("ALTER TABLE attendance DROP COLUMN IF EXISTS device_event_id")
    op.execute("ALTER TABLE attendance DROP COLUMN IF EXISTS source")
    op.execute("DROP TABLE IF EXISTS hikvision_employee_map")
    op.execute("DROP TABLE IF EXISTS hikvision_event")
    op.execute("DROP TABLE IF EXISTS hikvision_device")
