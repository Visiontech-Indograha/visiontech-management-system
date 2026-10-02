"""Absensi dipisah per jenis pekerja: lapangan absen di HP, kantor absen di web.

- `employee.attendance_mode` ('FIELD' | 'OFFICE'), diubah HR. Nilai awal: OFFICE bila akun karyawan
  memegang peran kantor (PM/OPS/HR/FINANCE/ASSET/ADMIN — daftar yang sama dengan R-21), lainnya FIELD.
- `attendance_source` mendapat nilai 'WEB'. Trigger geofence tidak berubah: swafoto hanya wajib
  untuk sumber MOBILE, jadi absen web di luar radius cukup berstatus NEEDS_REVIEW.

Revision ID: 0013_attendance_mode_web
Revises: 0012_final_report_signed
Create Date: 2026-10-01
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0013_attendance_mode_web"
down_revision: str | Sequence[str] | None = "0012_final_report_signed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("ALTER TYPE attendance_source ADD VALUE IF NOT EXISTS 'WEB'")
    op.execute(
        "ALTER TABLE employee ADD COLUMN attendance_mode text NOT NULL DEFAULT 'FIELD' "
        "CHECK (attendance_mode IN ('FIELD','OFFICE'))"
    )
    op.execute(
        """
        UPDATE employee e SET attendance_mode = 'OFFICE'
        WHERE EXISTS (SELECT 1 FROM app_user u JOIN user_role r ON r.user_id = u.id
                      WHERE u.employee_id = e.id
                        AND r.role IN ('PM','OPS','HR','FINANCE','ASSET','ADMIN'))
        """
    )
    op.execute("COMMENT ON COLUMN employee.attendance_mode IS "
               "'FIELD = absen lewat aplikasi HP; OFFICE = absen lewat web.'")


def downgrade() -> None:
    # Nilai enum 'WEB' tidak dapat dihapus PostgreSQL tanpa membuat ulang tipe; dibiarkan.
    op.execute("SET LOCAL search_path = vms, public")
    op.execute("ALTER TABLE employee DROP COLUMN IF EXISTS attendance_mode")
