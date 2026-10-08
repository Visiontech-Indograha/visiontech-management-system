from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_hse_service, incident_plan_access, plan_day_access
from app.core.security import CurrentUser
from app.schemas.hse import (
    DailyReportCreate,
    DailyReportResponse,
    IncidentCreate,
    IncidentResolve,
    IncidentResponse,
    ReportReviewRequest,
)
from app.services.access_service import PlanAccess, PlanNeed
from app.services.hse_service import HseService

router = APIRouter(prefix="/hse", tags=["HSE & Reports"])
_INCIDENT_VIEW_ACCESS = Depends(incident_plan_access(PlanNeed.VIEW))
_DAY_LEADER_ACCESS = Depends(plan_day_access(PlanNeed.LEADER))  # domain.js SAVE/SUBMIT_REPORT
_DAY_PM_UNIT_ACCESS = Depends(plan_day_access(PlanNeed.PM_UNIT))  # domain.js REVIEW_REPORT
# Laporan harian di bawah SK-nya (dok 05 §3.6, V-16); sebelumnya /hse/daily-reports/{day_id}.
days_router = APIRouter(prefix="/work-plans/{plan_id}/days", tags=["Daily Reports"])


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    plan_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    hse: HseService = Depends(get_hse_service),
) -> list[IncidentResponse]:
    """
    Mendapatkan daftar insiden untuk satu Surat Kerja (SK).
    Menampilkan insiden terbaru di urutan awal.
    SK asing/tak terlihat → 404.

    Query params:
    - plan_id: UUID dari Surat Kerja

    Return: Daftar insiden (list[IncidentResponse])
    """
    rows = await hse.list_incidents(current_user, plan_id)
    return [IncidentResponse(**r._mapping) for r in rows]


@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def report_incident(
    data: IncidentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    hse: HseService = Depends(get_hse_service),
) -> IncidentResponse:
    """
    Melaporkan insiden baru untuk SK yang sedang berlangsung.
    (Hanya ketua atau anggota pekerjaan ini, SK harus IN_PROGRESS).

    Body params:
    - data: Detail insiden yang dilaporkan (IncidentCreate)

    Return: Detail insiden yang direkam (IncidentResponse)
    """
    incident = await hse.report_incident(current_user, data.work_plan_id, data.category, data.severity,
                                         data.description, data.evidence_file_ids)
    return IncidentResponse(**incident._mapping)


@router.post("/incidents/{inc_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    inc_id: UUID,
    data: IncidentResolve,
    access: PlanAccess = _INCIDENT_VIEW_ACCESS,
    hse: HseService = Depends(get_hse_service),
) -> IncidentResponse:
    """
    Menyelesaikan masalah insiden. Hanya PM (unit SK), OPS, atau ASSET yang bisa mengeksekusi.

    Path params:
    - inc_id: UUID dari insiden

    Body params:
    - data: Catatan resolusi (IncidentResolve)

    Return: Detail insiden yang telah diselesaikan (IncidentResponse)
    """
    row = await hse.resolve_incident(access, inc_id, data.resolution_note)
    return IncidentResponse(**row._mapping)


@days_router.put("/{day_id}", response_model=DailyReportResponse)
async def upsert_daily_report(
    day_id: UUID,
    data: DailyReportCreate,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    hse: HseService = Depends(get_hse_service),
) -> DailyReportResponse:
    """
    Membuat atau memperbarui DRAFT laporan harian pekerjaan (Hanya Ketua Tim, SK IN_PROGRESS).

    Path params:
    - plan_id: UUID dari SK (di-routing)
    - day_id: UUID hari pelaksanaan SK

    Body params:
    - data: Data laporan harian (DailyReportCreate)

    Return: Laporan harian (DailyReportResponse)
    """
    report = await hse.save_daily_report(access, day_id, data.body, data.obstacle, data.evidence_file_ids)
    return DailyReportResponse(**report._mapping)


@days_router.post("/{day_id}/submit", response_model=DailyReportResponse)
async def submit_daily_report(
    day_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    hse: HseService = Depends(get_hse_service),
) -> DailyReportResponse:
    """
    Menyerahkan (submit) laporan harian yang berstatus DRAFT atau minta revisi ke manajer/PM.

    Path params:
    - plan_id: UUID dari SK
    - day_id: UUID hari pelaksanaan SK

    Return: Laporan harian dengan status tersubmit (DailyReportResponse)
    """
    report = await hse.submit_daily_report(access, day_id)
    return DailyReportResponse(**report._mapping)


@days_router.post("/{day_id}/review", response_model=DailyReportResponse)
async def review_daily_report(
    day_id: UUID,
    data: ReportReviewRequest,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    hse: HseService = Depends(get_hse_service),
) -> DailyReportResponse:
    """
    domain.js REVIEW_REPORT (V-24): PM unit/OPS menyetujui atau mengembalikan laporan harian yang diserahkan.

    Path params:
    - plan_id: UUID dari SK
    - day_id: UUID hari pelaksanaan SK

    Body params:
    - data: Data hasil review laporan (ReportReviewRequest)

    Return: Detail laporan harian pasca-review (DailyReportResponse)
    """
    report = await hse.review_daily_report(access, day_id, data.decision, data.note)
    return DailyReportResponse(**report._mapping)


@days_router.post("/{day_id}/tasks/{task_id}/toggle")
async def toggle_task(
    day_id: UUID,
    task_id: UUID,
    access: PlanAccess = _DAY_LEADER_ACCESS,
    hse: HseService = Depends(get_hse_service),
) -> dict[str, object]:
    """
    domain.js TOGGLE_TASK (V-23): ketua mencentang/menghapus centang tugas hari tersebut, selama laporan belum diserahkan.

    Path params:
    - plan_id: UUID SK (di-routing)
    - day_id: UUID hari eksekusi
    - task_id: UUID tugas yang dicentang

    Return: Status toggle (is_done) dari tugas tersebut
    """
    row = await hse.toggle_task(access, day_id, task_id)
    return {"id": str(row.id), "is_done": row.is_done}
