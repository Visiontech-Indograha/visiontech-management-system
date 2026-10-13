"""Tambah kolom photo_file_id ke tabel employee untuk foto profil.

Revision ID: 0037_employee_photo
Revises: 0036_face_threshold
Create Date: 2026-10-12

Menambahkan kolom photo_file_id (UUID, nullable) ke tabel employee
yang merujuk ke vms.file_object.id untuk foto profil karyawan.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0037_employee_photo"
down_revision: str | None = "0036_face_threshold"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `db/01_schema.sql` (jalur bootstrap CI/server) sudah membuat kolom DAN foreign key ini.
    # Karena itu keduanya WAJIB idempoten: PostgreSQL tidak mendukung
    # `ADD CONSTRAINT IF NOT EXISTS`, sehingga tanpa blok DO ini migrasi gagal dengan
    # DuplicateObjectError di database yang dibangun dari db/*.sql (insiden deploy 2026-10-13).
    op.execute("ALTER TABLE vms.employee ADD COLUMN IF NOT EXISTS photo_file_id uuid")
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE vms.employee
            ADD CONSTRAINT fk_employee_photo_file
            FOREIGN KEY (photo_file_id) REFERENCES vms.file_object(id)
            ON DELETE SET NULL;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE vms.employee DROP CONSTRAINT IF EXISTS fk_employee_photo_file")
    op.execute("ALTER TABLE vms.employee DROP COLUMN IF EXISTS photo_file_id")
