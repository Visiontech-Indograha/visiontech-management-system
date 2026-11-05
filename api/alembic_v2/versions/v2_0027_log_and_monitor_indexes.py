"""Indeks untuk jejak audit (F-10) dan pemantauan absensi harian (F-11).

Expand-only: hanya menambah indeks, tanpa mengubah data atau constraint.

- `app_activity_logs` (partisi bulanan, F-10): indeks `(created_at DESC, log_id)` untuk
  `ORDER BY a.created_at DESC` pada halaman audit. PostgreSQL tidak mendukung
  `CREATE INDEX CONCURRENTLY` pada tabel berpartisi, maka indeks dibuat per partisi
  secara `CONCURRENTLY`, lalu indeks induk dibuat `ON ONLY` (tanpa membangun ulang)
  dan setiap indeks partisi dilampirkan (`ATTACH PARTITION`). Partisi yang dibuat
  kemudian (lifespan, `ensure_activity_log_partitions`) otomatis menerima indeks induk.
- `attendance` (F-11): indeks parsial `(attendance_date, om_approval_status) WHERE delete_at IS NULL`.
  Melayani `attendance_monitor_repository` (`attendance_date = :d`, `attendance_date BETWEEN`,
  dan `om_approval_status = 'PENDING_OM'`) serta rentang tanggal di `monitoring_repository`.

Revision ID: v2_0027
Revises: v2_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0027"
down_revision: str | None = "v2_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT_LOG_IDX = "ix_app_activity_logs_created_log"


def _partition_idx(rel: str) -> str:
    return f"ix_{rel}_created_log"


def _log_partitions() -> list[str]:
    rows = op.get_bind().execute(
        sa.text(
            """
            SELECT c.relname
            FROM pg_inherits i
            JOIN pg_class c ON c.oid = i.inhrelid
            JOIN pg_class p ON p.oid = i.inhparent
            JOIN pg_namespace n ON n.oid = p.relnamespace
            WHERE p.relname = 'app_activity_logs' AND n.nspname = 'public'
            ORDER BY c.relname
            """
        )
    )
    return [str(r[0]) for r in rows]


def _attached_partitions() -> set[str]:
    """Partisi yang indeks partisinya sudah terlampir ke indeks induk (kosong bila indeks induk belum ada)."""
    rows = op.get_bind().execute(
        sa.text(
            """
            SELECT t.relname
            FROM pg_inherits i
            JOIN pg_class p ON p.oid = i.inhparent
            JOIN pg_class ci ON ci.oid = i.inhrelid
            JOIN pg_index x ON x.indexrelid = ci.oid
            JOIN pg_class t ON t.oid = x.indrelid
            WHERE p.relname = :parent
            """
        ),
        {"parent": _PARENT_LOG_IDX},
    )
    return {str(r[0]) for r in rows}


def upgrade() -> None:
    parts = _log_partitions()
    attached = _attached_partitions()
    with op.get_context().autocommit_block():
        for rel in parts:
            if rel in attached:
                continue
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_partition_idx(rel)} "
                f"ON public.{rel} (created_at DESC, log_id)"
            )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {_PARENT_LOG_IDX} "
            "ON ONLY public.app_activity_logs (created_at DESC, log_id)"
        )
        for rel in parts:
            if rel in attached:
                continue
            op.execute(f"ALTER INDEX public.{_PARENT_LOG_IDX} ATTACH PARTITION public.{_partition_idx(rel)}")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_attendance_date_status "
            "ON attendance (attendance_date, om_approval_status) WHERE delete_at IS NULL"
        )


def downgrade() -> None:
    # Menghapus indeks induk ikut melepas dan menghapus indeks partisi yang terlampir.
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX IF EXISTS public.{_PARENT_LOG_IDX}")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_attendance_date_status")
