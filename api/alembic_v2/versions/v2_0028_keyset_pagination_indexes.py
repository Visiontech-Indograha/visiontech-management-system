"""Indeks pendukung paginasi keyset: lembur dan filter jenis entitas pada log audit.

Expand-only: hanya menambah indeks (tanpa ubah data/constraint). Dasar keputusan (EXPLAIN pada 200 rb baris
sintetis) ada di deskripsi PR.

- `overtime`: `(create_at DESC, overtime_id DESC) WHERE delete_at IS NULL` untuk daftar semua, dan
  `(employee_id, create_at DESC, overtime_id DESC) WHERE delete_at IS NULL` untuk daftar per karyawan.
  Sebelumnya: Seq Scan + top-N sort (semua) dan Bitmap Heap + sort (per karyawan).
- `app_activity_logs` (partisi bulanan): `(entity_table, created_at DESC, log_id)` untuk filter `entity_type`
  dengan urutan yang sama seperti halaman audit. Pola partisi sama dengan v2_0027: indeks per partisi
  `CONCURRENTLY`, induk `ON ONLY`, lalu `ATTACH PARTITION`.
- Tidak ditambah: audit tanpa filter (sudah `ix_app_activity_logs_created_log`, v2_0027) dan absensi
  (`idx_attendance_emp_date` dan `ix_attendance_date_status` + Incremental Sort sudah murah).

Revision ID: v2_0028
Revises: v2_0027
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2_0028"
down_revision: str | None = "v2_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARENT = "ix_app_activity_logs_entity_created_log"
_OT_ALL = "ix_overtime_created_keyset"
_OT_EMP = "ix_overtime_employee_created_keyset"


def _part_idx(rel: str) -> str:
    return f"ix_{rel}_entity_created_log"


def _partitions() -> list[str]:
    rows = op.get_bind().execute(
        sa.text(
            """
            SELECT c.relname FROM pg_inherits i
            JOIN pg_class c ON c.oid = i.inhrelid
            JOIN pg_class p ON p.oid = i.inhparent
            JOIN pg_namespace n ON n.oid = p.relnamespace
            WHERE p.relname = 'app_activity_logs' AND n.nspname = 'public'
            ORDER BY c.relname
            """
        )
    )
    return [str(r[0]) for r in rows]


def _attached() -> set[str]:
    rows = op.get_bind().execute(
        sa.text(
            """
            SELECT t.relname FROM pg_inherits i
            JOIN pg_class p ON p.oid = i.inhparent
            JOIN pg_index x ON x.indexrelid = i.inhrelid
            JOIN pg_class t ON t.oid = x.indrelid
            WHERE p.relname = :parent
            """
        ),
        {"parent": _PARENT},
    )
    return {str(r[0]) for r in rows}


def _drop_invalid(names: list[str]) -> None:
    """Indeks CONCURRENTLY yang gagal tertinggal INVALID dan akan dilewati oleh IF NOT EXISTS: buang dulu."""
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
    parts = _partitions()
    attached = _attached()
    with op.get_context().autocommit_block():
        _drop_invalid([_OT_ALL, _OT_EMP, *[_part_idx(r) for r in parts if r not in attached]])
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_OT_ALL} "
            "ON overtime (create_at DESC, overtime_id DESC) WHERE delete_at IS NULL"
        )
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_OT_EMP} "
            "ON overtime (employee_id, create_at DESC, overtime_id DESC) WHERE delete_at IS NULL"
        )
        for rel in parts:
            if rel in attached:
                continue
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_part_idx(rel)} "
                f"ON public.{rel} (entity_table, created_at DESC, log_id)"
            )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {_PARENT} "
            "ON ONLY public.app_activity_logs (entity_table, created_at DESC, log_id)"
        )
        for rel in parts:
            if rel in attached:
                continue
            op.execute(f"ALTER INDEX public.{_PARENT} ATTACH PARTITION public.{_part_idx(rel)}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        # Menghapus indeks induk ikut menghapus indeks partisi yang terlampir.
        op.execute(f"DROP INDEX IF EXISTS public.{_PARENT}")
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{_OT_EMP}")
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{_OT_ALL}")
