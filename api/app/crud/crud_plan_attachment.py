"""
app/crud/crud_plan_attachment.py
Lampiran draf SK (V-29, domain.js SAVE_ATTACHMENTS): daftar berkas berurutan per SK.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanAttachment(CRUDBase):

    async def list_for_plan(self, plan_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT CAST(a.file_id AS text) AS file_id, f.file_name, f.mime_type, f.byte_size, a.sort_order
            FROM vms.work_plan_attachment a JOIN vms.file_object f ON f.id = a.file_id
            WHERE a.work_plan_id = :plan
            ORDER BY a.sort_order
            """,
            {"plan": plan_id},
        ))

    async def replace(self, plan_id: UUID | str, file_ids: list[UUID]) -> None:
        """Ganti seluruh lampiran; urutan daftar = sort_order."""
        await self.execute("DELETE FROM vms.work_plan_attachment WHERE work_plan_id = :plan", {"plan": plan_id})
        if file_ids:
            await self.execute(
                """
                INSERT INTO vms.work_plan_attachment (work_plan_id, file_id, sort_order)
                SELECT :plan, unnest(CAST(:fids AS uuid[])), unnest(CAST(:ords AS int[]))
                """,
                {"plan": plan_id, "fids": [str(f) for f in file_ids], "ords": list(range(len(file_ids)))}
            )
