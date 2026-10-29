"""Peran sistem FINANCE (Master Schema V2): melihat & mengekspor absensi seluruh karyawan.

`ALTER TYPE ... ADD VALUE` tidak boleh berjalan di dalam transaksi (PostgreSQL < 12 melarangnya; di
versi baru nilai baru belum bisa dipakai dalam transaksi yang sama), maka dijalankan di luar transaksi.

Revision ID: v2_0010
Revises: v2_0009
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0010"
down_revision: str | None = "v2_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE system_role_enum ADD VALUE IF NOT EXISTS 'FINANCE'")


def downgrade() -> None:
    # PostgreSQL tidak mendukung hapus nilai enum; nilai 'FINANCE' dibiarkan. Pengguna FINANCE diturunkan
    # perannya secara manual bila perlu.
    pass
