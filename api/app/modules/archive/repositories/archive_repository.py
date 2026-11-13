"""SQL Arsip. Nama tabel/kolom hanya dari konfigurasi tetap `ARCHIVE_MODULES` (bukan input pengguna)."""
from __future__ import annotations

from typing import Any

from app.core.list_params import MAX_ROWS_UNPAGED
from app.core.repository import BaseRepository
from app.modules.archive.schemas.archive_modules import ArchiveModule


class ArchiveRepository(BaseRepository):
    async def list_deleted(self, mod: ArchiveModule, offices: list[str] | None) -> list[Any]:
        code = f"{mod.code_col}::text" if mod.code_col else "NULL::text"
        scope = f"AND {mod.office_col} = ANY(CAST(:offices AS uuid[]))" if mod.office_col and offices else ""
        rows = await self.fetchall(
            f"SELECT {mod.pk}::text AS id, {mod.name_col}::text AS name, {code} AS code, delete_at "
            f"FROM {mod.table} WHERE delete_at IS NOT NULL {scope} "
            f"ORDER BY delete_at DESC, {mod.pk} LIMIT :cap",
            {"cap": MAX_ROWS_UNPAGED, **({"offices": offices} if scope else {})},
        )
        return list(rows)

    async def get_any(self, mod: ArchiveModule, item_id: str) -> Any:
        """Satu baris (aktif atau terhapus) beserta kantornya (bila modul punya kantor)."""
        code = f"{mod.code_col}::text" if mod.code_col else "NULL::text"
        office = f"{mod.office_col}::text" if mod.office_col else "NULL::text"
        return await self.fetchone(
            f"SELECT {mod.pk}::text AS id, {mod.name_col}::text AS name, {code} AS code, delete_at, "
            f"{office} AS office_id FROM {mod.table} WHERE {mod.pk} = CAST(:id AS uuid)", {"id": item_id})

    async def unique_conflict(self, mod: ArchiveModule, item_id: str) -> bool:
        if not mod.unique_exprs:
            return False
        conds = " OR ".join(f"{e.format(r='a')} = {e.format(r='d')}" for e in mod.unique_exprs)
        row = await self.fetchone(
            f"SELECT 1 FROM {mod.table} a JOIN {mod.table} d ON d.{mod.pk} = CAST(:id AS uuid) "
            f"WHERE a.delete_at IS NULL AND a.{mod.pk} <> d.{mod.pk} AND ({conds}) LIMIT 1", {"id": item_id})
        return row is not None

    async def missing_parent(self, mod: ArchiveModule, item_id: str) -> str | None:
        """Nama induk (divisi, atasan) yang masih diarsipkan/tidak ada, atau None bila semua aktif."""
        for col, table, ppk, label in mod.parents:
            row = await self.fetchone(
                f"SELECT 1 FROM {mod.table} d WHERE d.{mod.pk} = CAST(:id AS uuid) AND d.{col} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM {table} p WHERE p.{ppk} = d.{col} AND p.delete_at IS NULL)",
                {"id": item_id})
            if row is not None:
                return label
        return None

    async def restore(self, mod: ArchiveModule, item_id: str) -> bool:
        """Pulihkan hanya bila masih terhapus (kondisi pada UPDATE); False = tidak ada baris yang berubah."""
        row = await self.fetchone(
            f"UPDATE {mod.table} SET delete_at = NULL, update_at = now() "
            f"WHERE {mod.pk} = CAST(:id AS uuid) AND delete_at IS NOT NULL RETURNING {mod.pk}", {"id": item_id})
        return row is not None

