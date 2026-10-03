"""
Laporan harian berjenjang & dokumen laporan (alur SK v2 PR2, flowchart SK2-E): anggota → ketua → PM.
Tipis (dok 12 §2): aturan di services/member_report_service.py, SQL di crud/crud_member_report.py.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.deps import get_member_report_service, plan_access, plan_day_access
from app.schemas.plan_draft import MemberReportIn, MemberReportOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.member_report_service import MemberReportService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Daily Reports"])
_DAY_VIEW = Depends(plan_day_access(PlanNeed.VIEW))
_DAY_MEMBER = Depends(plan_day_access(PlanNeed.MEMBER))
_VIEW = Depends(plan_access(PlanNeed.VIEW))


@router.get("/days/{day_id}/member-reports", response_model=list[MemberReportOut])
async def member_reports(day_id: UUID, access: PlanAccess = _DAY_VIEW,
                         member_report_service: MemberReportService = Depends(get_member_report_service),
                         ) -> list[MemberReportOut]:
    """Laporan anggota satu hari — dibaca ketua untuk disusun, dan PM saat memeriksa."""
    return [MemberReportOut(**r._mapping) for r in await member_report_service.list_for_day(day_id)]


@router.get("/days/{day_id}/member-report", response_model=MemberReportOut | None)
async def my_member_report(day_id: UUID, access: PlanAccess = _DAY_MEMBER,
                           member_report_service: MemberReportService = Depends(get_member_report_service),
                           ) -> MemberReportOut | None:
    row = await member_report_service.mine(access, day_id)
    return MemberReportOut(**row._mapping) if row else None


@router.put("/days/{day_id}/member-report", response_model=MemberReportOut)
async def save_member_report(day_id: UUID, data: MemberReportIn, access: PlanAccess = _DAY_MEMBER,
                             member_report_service: MemberReportService = Depends(get_member_report_service),
                             ) -> MemberReportOut:
    row = await member_report_service.save(access, day_id, data.body, data.obstacle, data.evidence_file_ids)
    return MemberReportOut(**row._mapping)


@router.post("/days/{day_id}/member-report/send", response_model=MemberReportOut)
async def send_member_report(day_id: UUID, access: PlanAccess = _DAY_MEMBER,
                             member_report_service: MemberReportService = Depends(get_member_report_service),
                             ) -> MemberReportOut:
    """Anggota mengirim laporannya ke ketua tim (notifikasi ke ketua)."""
    row = await member_report_service.send(access, day_id)
    return MemberReportOut(**row._mapping)


@router.get("/days/{day_id}/report/html", response_class=HTMLResponse)
async def daily_report_html(day_id: UUID, access: PlanAccess = _DAY_VIEW,
                            member_report_service: MemberReportService = Depends(get_member_report_service),
                            ) -> HTMLResponse:
    """Dokumen A4 laporan harian (isi ketua + laporan anggota + pemeriksaan PM)."""
    return HTMLResponse(await member_report_service.daily_report_html(access, day_id))


@router.get("/weekly/{week}/report/html", response_class=HTMLResponse)
async def weekly_report_html(week: int, access: PlanAccess = _VIEW,
                             member_report_service: MemberReportService = Depends(get_member_report_service),
                             ) -> HTMLResponse:
    return HTMLResponse(await member_report_service.weekly_report_html(access, f"Laporan Mingguan {week}"))
