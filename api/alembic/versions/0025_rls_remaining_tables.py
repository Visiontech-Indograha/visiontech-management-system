"""RLS batas tenant untuk enam tabel ber-organization_id yang belum dilindungi (P9-2 lanjutan, 2026-10-08).

Revision ID: 0025_rls_remaining_tables
Revises: 0024_runtime_role
Create Date: 2026-10-08

Sejak 0024 API tersambung sebagai `vms_api` yang tunduk RLS. Tabel `site`, `file_object`, `notification`,
`attendance_device_key`, `attendance_offline_event`, dan `signature_serial_counter` masih bergantung sepenuhnya pada
filter organisasi di crud. Kebijakan di sini = batas tenant (sama dengan keputusan docs/10 Bagian C); pembatasan per
orang (penerima notifikasi, pemilik kunci perangkat) tetap di service.

`app_user` sengaja TIDAK diberi RLS: login dan rotasi token mencari akun sebelum identitas/organisasi diketahui.
Isi SQL sama dengan bagian akhir `db/05_face.sql`.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0025_rls_remaining_tables"
down_revision: str | None = "0024_runtime_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("site", "file_object", "notification", "attendance_device_key", "attendance_offline_event",
          "signature_serial_counter")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE vms.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_isolation ON vms.{table} USING (organization_id = vms.current_org_id())")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_isolation ON vms.{table}")
        op.execute(f"ALTER TABLE vms.{table} DISABLE ROW LEVEL SECURITY")
