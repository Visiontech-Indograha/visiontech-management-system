"""
app/shared/attachments/repository.py
Query lampiran pengajuan. Nama tabel/kolom berasal dari konstanta `AttachmentKind` (bukan input pengguna).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

MAX_ATTACHMENTS = 5


@dataclass(frozen=True)
class AttachmentKind:
    label: str          # nama objek untuk pesan galat
    parent_table: str
    parent_pk: str
    table: str
    parent_fk: str
    pending_status: str  # satu-satunya status yang masih membuka lampiran


OVERTIME = AttachmentKind("Lembur", "overtime", "overtime_id",
                          "overtime_attachment", "overtime_id", "PENDING_PM")
MESS = AttachmentKind("Hunian mess", "company_mess_stay", "mess_stay_id",
                      "mess_stay_attachment", "mess_stay_id", "REQUESTED")


class AttachmentRepository(BaseRepository):
    async def parent(self, kind: AttachmentKind, parent_id: UUID | str, *, lock: bool = False) -> Any:
        """Baris induk (status, pemohon, kantor pemohon). `lock` = kunci baris: keputusan dan lampiran
        tidak bisa berjalan bersamaan."""
        extra = ", p.daily_plan_id::text AS daily_plan_id" if kind is OVERTIME else ", NULL AS daily_plan_id"
        return await self.fetchone(
            f"SELECT p.status, p.employee_id::text AS employee_id, e.office_id::text AS office_id{extra} "
            f"FROM {kind.parent_table} p JOIN employee e ON e.employee_id = p.employee_id "
            f"WHERE p.{kind.parent_pk} = CAST(:id AS uuid) AND p.delete_at IS NULL"
            + (" FOR UPDATE OF p" if lock else ""),
            {"id": str(parent_id)},
        )

    async def items(self, kind: AttachmentKind, parent_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            f"SELECT a.file_object_id AS file_id, f.file_name, f.mime_type, f.byte_size, "
            f"a.added_by_user_id::text AS added_by, a.create_at AS created_at "
            f"FROM {kind.table} a JOIN file_object f ON f.id = a.file_object_id "
            f"WHERE a.{kind.parent_fk} = CAST(:id AS uuid) ORDER BY a.create_at, a.attachment_id",
            {"id": str(parent_id)},
        ))

    async def count(self, kind: AttachmentKind, parent_id: UUID | str) -> int:
        return int(await self.scalar(
            f"SELECT count(*) FROM {kind.table} WHERE {kind.parent_fk} = CAST(:id AS uuid)", {"id": str(parent_id)}
        ) or 0)

    async def file(self, file_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT id, office_id::text AS office_id, uploaded_by::text AS uploaded_by FROM file_object "
            "WHERE id = CAST(:id AS uuid)",
            {"id": str(file_id)},
        )

    async def insert(self, kind: AttachmentKind, parent_id: UUID | str, file_id: UUID | str, office_id: str,
                     user_id: str) -> None:
        await self.execute(
            f"INSERT INTO {kind.table} (office_id, {kind.parent_fk}, file_object_id, added_by_user_id) "
            "VALUES (CAST(:o AS uuid), CAST(:p AS uuid), CAST(:f AS uuid), CAST(:u AS uuid)) "
            f"ON CONFLICT ({kind.parent_fk}, file_object_id) DO NOTHING",
            {"o": office_id, "p": str(parent_id), "f": str(file_id), "u": user_id},
        )

    async def get_link(self, kind: AttachmentKind, parent_id: UUID | str, file_id: UUID | str) -> Any:
        return await self.fetchone(
            f"SELECT a.added_by_user_id::text AS added_by FROM {kind.table} a "
            f"WHERE a.{kind.parent_fk} = CAST(:p AS uuid) AND a.file_object_id = CAST(:f AS uuid)",
            {"p": str(parent_id), "f": str(file_id)},
        )

    async def delete(self, kind: AttachmentKind, parent_id: UUID | str, file_id: UUID | str) -> None:
        await self.execute(
            f"DELETE FROM {kind.table} WHERE {kind.parent_fk} = CAST(:p AS uuid) "
            "AND file_object_id = CAST(:f AS uuid)",
            {"p": str(parent_id), "f": str(file_id)},
        )

    async def storage_key(self, file_id: UUID | str) -> str | None:
        key = await self.scalar("SELECT storage_key FROM file_object WHERE id = CAST(:id AS uuid)",
                                {"id": str(file_id)})
        return str(key) if key else None

    async def division_pm_of(self, employee_id: UUID | str) -> str | None:
        v = await self.scalar(
            "SELECT d.pm_id::text FROM employee e JOIN division d ON d.division_id = e.division_id "
            "WHERE e.employee_id = CAST(:id AS uuid)", {"id": str(employee_id)})
        return str(v) if v else None
