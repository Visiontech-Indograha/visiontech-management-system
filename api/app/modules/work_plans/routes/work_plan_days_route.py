"""
app/modules/work_plans/routes/work_plan_days_route.py

Rute endpoint HTTP untuk membaca hari kerja SK (/work-plans/{plan_id}/days).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response

from app.api.deps import plan_access
from app.modules.work_plans.controllers.work_plan_days_controller import (
    WorkPlanDaysController,
)
from app.modules.work_plans.schemas.work_plan_schema import PlanDayOut
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))


@router.get("", response_model=list[PlanDayOut])
async def list_plan_days(
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanDaysController = Depends(),
) -> list[PlanDayOut]:
    """Mengambil daftar hari kerja beserta tugas dan laporan harian dari SK (GET)."""
    return await controller.handle_list_days(access)


@router.get("/{day_id}/preview", response_class=HTMLResponse)
async def preview_plan_day(
    plan_id: UUID,
    day_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanDaysController = Depends(),
) -> HTMLResponse:
    """Pratinjau HTML rencana kerja harian (GET)."""
    return await controller.handle_preview_day(plan_id, day_id)


@router.get("/{day_id}/export", response_class=Response)
async def export_plan_day(
    plan_id: UUID,
    day_id: UUID,
    format: str = Query(default="pdf", pattern="^(pdf|docx|xlsx|pptx)$"),
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanDaysController = Depends(),
) -> Response:
    """Mengunduh rencana kerja harian dalam berbagai format: PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX) (GET)."""
    return await controller.handle_export_day(plan_id, day_id, format, inline=False)


@router.get("/{day_id}/pdf", response_class=Response)
async def preview_plan_day_pdf(
    plan_id: UUID,
    day_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    controller: WorkPlanDaysController = Depends(),
) -> Response:
    """Pratinjau PDF rencana kerja harian langsung di browser (inline) (GET)."""
    return await controller.handle_export_day(plan_id, day_id, "pdf", inline=True)


__all__ = ["router"]
