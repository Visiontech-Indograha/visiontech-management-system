"""
app/modules/work_plans/routes/work_plan_reports_route.py

Rute endpoint HTTP untuk laporan harian berjenjang & dokumen laporan (/work-plans/{plan_id}).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user, plan_access, plan_day_access
from app.modules.work_plans.controllers.work_plan_reports_controller import (
    WorkPlanReportsController,
)
from app.modules.work_plans.schemas.work_plan_schema import (
    MemberReportIn,
    MemberReportOut,
)
from app.services.access_service import PlanAccess, PlanNeed

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Daily Reports"])
_DAY_VIEW = Depends(plan_day_access(PlanNeed.VIEW))
_DAY_MEMBER = Depends(plan_day_access(PlanNeed.MEMBER))
_VIEW = Depends(plan_access(PlanNeed.VIEW))


@router.get("/days/{day_id}/member-reports", response_model=list[MemberReportOut])
async def member_reports(
    day_id: UUID,
    access: PlanAccess = _DAY_VIEW,
    controller: WorkPlanReportsController = Depends(),
) -> list[MemberReportOut]:
    """Mendapatkan daftar laporan anggota untuk satu hari tertentu (GET)."""
    return await controller.handle_member_reports(day_id)


@router.get("/days/{day_id}/member-report", response_model=MemberReportOut | None)
async def my_member_report(
    day_id: UUID,
    access: PlanAccess = _DAY_MEMBER,
    controller: WorkPlanReportsController = Depends(),
) -> MemberReportOut | None:
    """Mengambil draf laporan harian milik anggota itu sendiri (GET)."""
    return await controller.handle_my_member_report(access, day_id)


@router.put("/days/{day_id}/member-report", response_model=MemberReportOut)
async def save_member_report(
    day_id: UUID,
    data: MemberReportIn,
    access: PlanAccess = _DAY_MEMBER,
    controller: WorkPlanReportsController = Depends(),
) -> MemberReportOut:
    """Menyimpan draf laporan harian dari seorang anggota (PUT)."""
    return await controller.handle_save_member_report(access, day_id, data)


@router.post("/days/{day_id}/member-report/send", response_model=MemberReportOut)
async def send_member_report(
    day_id: UUID,
    access: PlanAccess = _DAY_MEMBER,
    controller: WorkPlanReportsController = Depends(),
) -> MemberReportOut:
    """Anggota mengirim laporannya ke ketua tim (POST)."""
    return await controller.handle_send_member_report(access, day_id)


@router.get("/days/{day_id}/report/html", response_class=HTMLResponse)
async def daily_report_html(
    day_id: UUID,
    access: PlanAccess = _DAY_VIEW,
    controller: WorkPlanReportsController = Depends(),
) -> HTMLResponse:
    """Mendapatkan dokumen A4 laporan harian dalam format HTML (GET)."""
    return await controller.handle_daily_report_html(access, day_id)


@router.get("/weekly/{week}/report/html", response_class=HTMLResponse)
async def weekly_report_html(
    week: int,
    access: PlanAccess = _VIEW,
    controller: WorkPlanReportsController = Depends(),
) -> HTMLResponse:
    """Mendapatkan dokumen laporan mingguan dalam format HTML (GET)."""
    return await controller.handle_weekly_report_html(access, week)


@router.get("/exports")
async def list_plan_exports(
    plan_id: UUID,
    access: PlanAccess = _VIEW,
    db: AsyncSession = Depends(get_db_with_user),
) -> list[dict[str, Any]]:
    """Daftar ekspor template dokumen (DOCX, PPTX, PDF, XLSX) dari public.document_template_export."""
    rows = await db.execute(
        text(
            """
            SELECT
                dte.export_id,
                dte.completion_id,
                dte.template_type,
                dte.master_template_path,
                dte.export_format,
                dte.file_output_url,
                dte.generated_by_id,
                dte.create_at
            FROM public.document_template_export dte
            JOIN public.work_completion wc ON wc.completion_id = dte.completion_id
            WHERE (wc.weekly_plan_id = :plan OR wc.daily_plan_id = :plan OR dte.completion_id = :plan)
              AND dte.delete_at IS NULL
            ORDER BY dte.create_at DESC
            """
        ),
        {"plan": plan_id},
    )
    return [dict(r._mapping) for r in rows]


__all__ = ["router"]
