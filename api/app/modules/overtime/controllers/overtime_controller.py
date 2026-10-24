"""
app/modules/overtime/controllers/overtime_controller.py

Controller orkestrasi use case pengajuan lembur dan rekapitulasi lembur bulanan.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.overtime.dependencies import get_overtime_service
from app.modules.overtime.schemas.overtime_schema import (
    OvertimeCreate,
    OvertimeRecapRow,
    OvertimeResponse,
    OvertimeReview,
)
from app.modules.overtime.services.overtime_service import OvertimeService


class OvertimeController:
    """
    Controller use case pengajuan lembur tim lapangan, persetujuan PM/OPS, dan rekap lembur.
    """

    def __init__(
        self,
        overtime_service: OvertimeService = Depends(get_overtime_service),
    ) -> None:
        self.overtime_service = overtime_service

    async def handle_delete(self, current_user: CurrentUser, ot_id: UUID) -> dict[str, str]:
        """Hapus permanen pengajuan lembur."""
        await self.overtime_service.delete(ot_id, current_user)
        return {"status": "deleted"}

    async def handle_report(self, current_user: CurrentUser, data: OvertimeCreate) -> OvertimeResponse:
        """Mengajukan lembur pada work plan yang aktif."""
        row = await self.overtime_service.report(current_user, data.daily_plan_id, data.hours, data.reason)
        return OvertimeResponse(**row._mapping)

    async def handle_list_by_plan(self, current_user: CurrentUser, daily_plan_id: UUID) -> list[OvertimeResponse]:
        """Mengambil daftar lembur untuk satu work plan."""
        rows = await self.overtime_service.list_by_plan(current_user, daily_plan_id)
        return [OvertimeResponse(**r._mapping) for r in rows]

    async def handle_review(self, current_user: CurrentUser, ot_id: UUID, data: OvertimeReview) -> OvertimeResponse:
        """Meninjau (menyetujui atau menolak) pengajuan lembur."""
        row = await self.overtime_service.review(current_user, ot_id, data.decision, data.note)
        return OvertimeResponse(**row._mapping)

    async def handle_recap(self, current_user: CurrentUser, month: str | None) -> list[OvertimeRecapRow]:
        """Mengambil data rekap lembur per karyawan per bulan."""
        month_date = date.fromisoformat(f"{month}-01") if month else None
        rows = await self.overtime_service.recap(current_user, month_date)
        return [OvertimeRecapRow(**r._mapping) for r in rows]
