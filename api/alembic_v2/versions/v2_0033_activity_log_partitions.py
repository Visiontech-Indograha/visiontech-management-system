"""Partisi bulanan `app_activity_logs` untuk 12 bulan ke depan + partisi DEFAULT (jalur pemilik).

Dulu dibuat saat startup aplikasi; peran runtime `vms_api` bukan pemilik tabel dan tak boleh DDL. Idempoten
(IF NOT EXISTS). Bulan berikutnya: `python -m app.cli buat-partisi` (cron host, peran pemilik).
Downgrade tidak menghapus partisi (berisi data audit).

Revision ID: v2_0033
Revises: v2_0032
"""

from collections.abc import Sequence
from datetime import date

from alembic import op

revision: str = "v2_0033"
down_revision: str | None = "v2_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    year, month = date.today().year, date.today().month
    for _ in range(13):
        ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
        op.execute(
            f"CREATE TABLE IF NOT EXISTS app_activity_logs_{year:04d}_{month:02d} PARTITION OF app_activity_logs "
            f"FOR VALUES FROM ('{year:04d}-{month:02d}-01 00:00:00+07') TO ('{ny:04d}-{nm:02d}-01 00:00:00+07')"
        )
        year, month = ny, nm
    op.execute("CREATE TABLE IF NOT EXISTS app_activity_logs_default PARTITION OF app_activity_logs DEFAULT")


def downgrade() -> None:
    # Sengaja kosong: partisi menyimpan jejak audit; tidak dibuang saat downgrade.
    pass
