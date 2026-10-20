"""
app/crud/crud_plan_attachment.py
Lampiran rencana kerja mingguan Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


class CRUDPlanAttachment(CRUDBase):
    """
    Kelas CRUD untuk mengelola data lampiran/berkas (attachment) Master Schema V2.
    """

    async def list_for_plan(self, plan_id: UUID | str) -> list[Any]:
        """Mendapatkan daftar lampiran dari sebuah Work Plan."""
        return await self.fetchall(
            """
            SELECT
                CAST(a.file_id AS text) AS file_id,
                f.file_name,
                f.mime_type,
                f.byte_size,
                a.sort_order
            FROM work_plan_attachment a
            JOIN file_object f ON f.id = a.file_id
            WHERE a.work_plan_id = CAST(:plan AS uuid)
            ORDER BY a.sort_order ASC, a.file_id ASC
            """,
            {"plan": plan_id},
        )

    async def replace(self, plan_id: UUID | str, file_ids: list[UUID]) -> None:
        """Ganti seluruh lampiran work plan."""
        await self.execute(
            "DELETE FROM work_plan_attachment WHERE work_plan_id = CAST(:plan AS uuid)",
            {"plan": plan_id},
        )
        if not file_ids:
            return

        for idx, fid in enumerate(file_ids):
            await self.execute(
                """
                INSERT INTO work_plan_attachment (work_plan_id, file_id, sort_order)
                VALUES (CAST(:plan AS uuid), CAST(:fid AS uuid), :ord)
                ON CONFLICT (work_plan_id, file_id) DO UPDATE SET sort_order = EXCLUDED.sort_order
                """,
                {"plan": plan_id, "fid": fid, "ord": idx},
            )

