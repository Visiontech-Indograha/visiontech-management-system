"""
Penghapusan data uji Master Schema V2 beserta seluruh baris turunannya.

Tidak ada daftar tabel manual: anak-anak sebuah baris ditemukan lewat katalog FK PostgreSQL lalu dihapus
lebih dulu (berjenjang), sehingga tabel baru otomatis ikut terbersihkan. Satu-satunya siklus FK di skema
(`employee.division_id` ↔ `division.om_id/pm_id`) diputus dulu dengan mengosongkan `employee.division_id`.
"""
from __future__ import annotations

from typing import Any

import psycopg2

_FK_SQL = """
    SELECT child.relname, child_col.attname, parent_col.attname
    FROM pg_constraint c
    JOIN pg_class child ON child.oid = c.conrelid
    JOIN pg_class parent ON parent.oid = c.confrelid
    JOIN pg_namespace n ON n.oid = child.relnamespace
    JOIN pg_attribute child_col ON child_col.attrelid = c.conrelid AND child_col.attnum = c.conkey[1]
    JOIN pg_attribute parent_col ON parent_col.attrelid = c.confrelid AND parent_col.attnum = c.confkey[1]
    WHERE c.contype = 'f' AND n.nspname = 'public' AND parent.relname = %s AND NOT child.relispartition
"""
_PK_SQL = """
    SELECT a.attname FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
    WHERE i.indrelid = %s::regclass AND i.indisprimary
"""


def _pk(cur: Any, table: str) -> str | None:
    cur.execute(_PK_SQL, (f"public.{table}",))
    row = cur.fetchone()
    return row[0] if row else None


def purge_rows(cur: Any, table: str, column: str, values: list[Any], _depth: int = 0) -> None:
    """Hapus baris `table` dengan `column` ∈ `values`, setelah semua baris yang merujuknya dihapus."""
    if not values or _depth > 25:
        return
    values = [str(v) for v in values]
    cur.execute(f'SELECT DISTINCT "{column}" FROM public."{table}" WHERE "{column}"::text = ANY(%s)', (values,))
    keys = [str(r[0]) for r in cur.fetchall()]
    if not keys:
        return

    cur.execute(_FK_SQL, (table,))
    for child, child_col, parent_col in cur.fetchall():
        if child == table:
            continue
        if parent_col == column:
            refs = keys
        else:
            cur.execute(f'SELECT "{parent_col}" FROM public."{table}" WHERE "{column}"::text = ANY(%s)', (keys,))
            refs = [str(r[0]) for r in cur.fetchall() if r[0] is not None]
        child_pk = _pk(cur, child)
        if child_pk:
            cur.execute(f'SELECT "{child_pk}" FROM public."{child}" WHERE "{child_col}"::text = ANY(%s)', (refs,))
            purge_rows(cur, child, child_pk, [r[0] for r in cur.fetchall()], _depth + 1)
        else:
            cur.execute(f'DELETE FROM public."{child}" WHERE "{child_col}"::text = ANY(%s)', (refs,))
    cur.execute(f'DELETE FROM public."{table}" WHERE "{column}"::text = ANY(%s)', (keys,))


def purge_office(conn: psycopg2.extensions.connection, office_id: str) -> None:
    """Hapus kantor uji beserta karyawan, akun, divisi, tim, rencana kerja, absensi, dst. miliknya."""
    with conn.cursor() as cur:
        cur.execute("UPDATE public.employee SET division_id = NULL WHERE office_id = %s", (office_id,))
        purge_rows(cur, "office", "office_id", [office_id])
    conn.commit()


def purge_users(conn: psycopg2.extensions.connection, user_ids: list[str]) -> None:
    """Hapus akun uji tanpa karyawan (beserta sesi & turunannya)."""
    with conn.cursor() as cur:
        purge_rows(cur, "users", "user_id", user_ids)
    conn.commit()
