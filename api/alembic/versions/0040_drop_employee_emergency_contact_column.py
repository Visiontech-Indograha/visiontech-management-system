"""Hapus kolom lama emergency_contact dari tabel employee.

Revision ID: 0040_drop_employee_emergency_contact_column
Revises: 0039_checkout_face_only
Create Date: 2026-10-14

Kontak darurat karyawan kini dikelola secara terstruktur melalui tabel
terpisah vms.employee_emergency_contact (Alembic 0038), sehingga kolom teks
tunggal emergency_contact pada tabel vms.employee tidak lagi digunakan.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0040_drop_employee_emergency_contact_column"
down_revision: str | None = "0039_checkout_face_only"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE vms.employee DROP COLUMN IF EXISTS emergency_contact;")


def downgrade() -> None:
    op.execute("ALTER TABLE vms.employee ADD COLUMN IF NOT EXISTS emergency_contact text;")
