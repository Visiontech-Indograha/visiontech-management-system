"""Tambah tabel employee_emergency_contact untuk data kontak darurat karyawan.

Revision ID: 0038_employee_emergency_contact
Revises: 0037_employee_photo
Create Date: 2026-10-13

Membuat tabel vms.employee_emergency_contact dengan isolasi tenant RLS,
indeks, dan memindahkan data lama dari kolom employee.emergency_contact.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0038_employee_emergency_contact"
down_revision: str | None = "0037_employee_photo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vms.employee_emergency_contact (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id uuid NOT NULL REFERENCES vms.organization(id) ON DELETE CASCADE,
            employee_id     uuid NOT NULL REFERENCES vms.employee(id) ON DELETE CASCADE,
            name            text NOT NULL,
            relationship    text NOT NULL,
            phone           text NOT NULL,
            address         text,
            is_primary      boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_emergency_contact_emp ON vms.employee_emergency_contact (employee_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_employee_emergency_contact_org_emp "
        "ON vms.employee_emergency_contact (organization_id, employee_id)"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON vms.employee_emergency_contact TO vms_api")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON vms.employee_emergency_contact TO vms_app;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_readonly') THEN
                GRANT SELECT ON vms.employee_emergency_contact TO vms_readonly;
            END IF;
        END
        $$;
        """
    )

    op.execute("ALTER TABLE vms.employee_emergency_contact ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'vms'
                  AND tablename = 'employee_emergency_contact'
                  AND policyname = 'employee_emergency_contact_isolation'
            ) THEN
                CREATE POLICY employee_emergency_contact_isolation ON vms.employee_emergency_contact
                USING (organization_id = vms.current_org_id());
            END IF;
        END
        $$;
        """
    )

    # Migrasi data lama dari employee.emergency_contact jika ada
    op.execute(
        """
        INSERT INTO vms.employee_emergency_contact (organization_id, employee_id, name, relationship, phone, is_primary)
        SELECT e.organization_id, e.id, e.emergency_contact, 'Keluarga', '-', true
        FROM vms.employee e
        WHERE e.emergency_contact IS NOT NULL AND trim(e.emergency_contact) != ''
          AND NOT EXISTS (
              SELECT 1 FROM vms.employee_emergency_contact c WHERE c.employee_id = e.id
          )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS vms.employee_emergency_contact")
