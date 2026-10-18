"""
app/modules/work_plans/controllers/work_plan_days_controller.py

Controller orkestrasi use case pembacaan hari kerja dan tugas harian SK.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.responses import HTMLResponse, Response

from app.api.deps import get_plan_day_service, get_plan_draft_service
from app.core.errors import AppError
from app.modules.work_plans.schemas.work_plan_schema import PlanDayOut
from app.modules.work_plans.services.work_plan_service import PlanDayService, PlanDraftService
from app.services.access_service import PlanAccess
from app.services.document_export_service import DocumentExportService
from app.services.pdf_service import render_plan_preview_html


def _out(row: Any) -> PlanDayOut:
    """Fungsi pembantu memetakan baris database ke skema PlanDayOut."""
    return PlanDayOut(**(row if isinstance(row, dict) else row._mapping))


class WorkPlanDaysController:
    """Controller pembacaan jadwal hari penugasan dan laporan harian per hari."""

    def __init__(
        self,
        plan_day_service: PlanDayService = Depends(get_plan_day_service),
        plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
    ) -> None:
        self.service = plan_day_service
        self.draft_service = plan_draft_service

    async def handle_list_days(
        self,
        access: PlanAccess,
    ) -> list[PlanDayOut]:
        """Mengambil daftar hari kerja, tugas, dan status laporan harian rencana kerja."""
        return [_out(row) for row in await self.service.list_days(access)]

    async def handle_preview_day(self, plan_id: UUID, day_id: UUID) -> HTMLResponse:
        """Pratinjau HTML rencana kerja harian spesifik."""
        detail = await self.draft_service.detail(plan_id)
        detail["days"] = [d for d in detail.get("days", []) if str(d.get("id")) == str(day_id)]
        return HTMLResponse(render_plan_preview_html(detail))

    async def handle_export_day(
        self,
        plan_id: UUID,
        day_id: UUID,
        format_type: str,
        inline: bool = False,
    ) -> Response:
        """Mengunduh rencana kerja harian spesifik dalam format pilihan (PDF, DOCX, XLSX, PPTX)."""
        detail = await self.draft_service.detail(plan_id)
        day_list = [d for d in detail.get("days", []) if str(d.get("id")) == str(day_id)]
        if not day_list:
            raise AppError("NOT_FOUND", "Hari rencana kerja tidak ditemukan.", status=404)
        detail["days"] = day_list
        day_date = str(day_list[0].get("work_date") or "")[:10]
        number = (detail.get("plan", {}).get("number") or f"PLAN-{str(plan_id)[:8]}").replace("/", "-")
        filename_base = f"{number}-DAILY-{day_date}"

        fmt = format_type.lower()
        if fmt == "pdf":
            content = DocumentExportService.export_pdf(detail)
            media_type = "application/pdf"
            ext = "pdf"
        elif fmt == "docx":
            content = DocumentExportService.export_docx(detail)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ext = "docx"
        elif fmt == "xlsx":
            content = DocumentExportService.export_xlsx(detail)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        elif fmt == "pptx":
            content = DocumentExportService.export_pptx(detail)
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ext = "pptx"
        else:
            raise AppError("INVALID_FORMAT", f"Format {format_type} tidak didukung.", status=400)

        disposition = "inline" if inline else "attachment"
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'{disposition}; filename="{filename_base}.{ext}"'},
        )


__all__ = ["WorkPlanDaysController"]
