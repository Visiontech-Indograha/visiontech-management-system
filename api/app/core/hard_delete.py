"""
app/core/hard_delete.py
Hapus permanen satu baris beserta rujukannya (khusus SUPER_ADMIN, izin DELETE_ANY) + catatan audit.

Tabel yang merujuk baris ini dicari dari katalog PostgreSQL (bukan daftar tulisan tangan, agar tidak ada yang
terlewat saat skema bertambah):
- kolom rujukan bernama sama dengan PK (mis. `employee_id`) = data milik baris ini → ikut dihapus;
- kolom NOT NULL dengan nama lain (mis. `division.pm_id`, `team.leader_employee_id`) = baris ini memegang
  peran pada data orang lain → ditolak 409 sampai perannya dialihkan (jangan ikut menghapus divisi/tim);
- kolom boleh NULL → diisi NULL.
Bila masih ada data lain yang bergantung pada baris anak, DB menolak dan pemanggil menerima 409.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError

logger = logging.getLogger(__name__)

_REFERENCES = text(
    """
    SELECT c.conrelid::regclass::text AS tbl, a.attname AS col, a.attnotnull AS not_null
    FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
    WHERE c.contype = 'f' AND c.confrelid = CAST(:parent AS regclass) AND array_length(c.conkey, 1) = 1
    ORDER BY a.attnotnull, c.conrelid::regclass::text
    """
)


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def purge_row(db: AsyncSession, table: str, pk_column: str, row_id: UUID) -> None:
    """Hapus `table` baris `row_id` beserta rujukannya. Dipanggil dalam transaksi permintaan."""
    params = {"id": str(row_id)}
    refs = (await db.execute(_REFERENCES, {"parent": table})).all()
    blockers = []
    for ref in refs:
        if ref.not_null and ref.col != pk_column:
            hit = await db.execute(
                text(f"SELECT 1 FROM {ref.tbl} WHERE {_ident(ref.col)} = CAST(:id AS uuid) LIMIT 1"), params
            )
            if hit.first() is not None:
                blockers.append(f"{ref.tbl}.{ref.col}")
    if blockers:
        raise AppError(
            "STILL_REFERENCED",
            "Data ini masih memegang peran pada data lain (" + ", ".join(blockers) + "). "
            "Alihkan perannya terlebih dahulu sebelum menghapus permanen.",
            status=409,
            details={"references": blockers},
        )
    try:
        for ref in refs:
            target = ref.tbl
            if ref.not_null:
                await db.execute(text(f"DELETE FROM {target} WHERE {_ident(ref.col)} = CAST(:id AS uuid)"), params)
            else:
                await db.execute(
                    text(f"UPDATE {target} SET {_ident(ref.col)} = NULL WHERE {_ident(ref.col)} = CAST(:id AS uuid)"),
                    params,
                )
        await db.execute(text(f"DELETE FROM {_ident(table)} WHERE {_ident(pk_column)} = CAST(:id AS uuid)"), params)
    except IntegrityError as exc:
        raise AppError(
            "STILL_REFERENCED",
            "Data ini masih dipakai data lain sehingga belum bisa dihapus permanen.",
            status=409,
        ) from exc


async def write_delete_audit(
    db: AsyncSession,
    *,
    actor_user_id: str,
    actor_role: str,
    actor_email: str,
    entity_type: str,
    entity_id: UUID,
    detail: dict[str, Any] | None = None,
    action: str = "HARD_DELETE",
) -> None:
    """Catat siapa menghapus/mengubah apa di app_activity_logs (savepoint: gagal mencatat tidak membatalkan hapus)."""
    try:
        async with db.begin_nested():
            await db.execute(
                text(
                    "INSERT INTO app_activity_logs (actor_user_id, actor_role, platform, action, entity_table, "
                    "entity_id, changed_diff) VALUES (CAST(:uid AS uuid), :role, 'web_react', :action, :etype, "
                    "CAST(:eid AS uuid), CAST(:diff AS jsonb))"
                ),
                {
                    "uid": actor_user_id,
                    "role": actor_role[:30],
                    "action": action,
                    "etype": entity_type,
                    "eid": str(entity_id),
                    "diff": json.dumps({"actor_email": actor_email, **(detail or {})}),
                },
            )
    except Exception:
        logger.exception("Gagal menulis audit %s %s", action, entity_type)
