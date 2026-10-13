"""Laporan mingguan SK (V-25, dok 05 §3.6) — `domain.js` SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY."""
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_weekly_report_service, plan_access
from app.schemas.weekly_report import WeeklyReportRequest, WeeklyReportResponse, WeeklyReviewRequest
from app.services.access_service import PlanAccess, PlanNeed
from app.services.weekly_report_service import WeeklyReportService

router = APIRouter(prefix="/work-plans/{plan_id}/weekly", tags=["Weekly Reports"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))      # domain.js SAVE/SUBMIT_WEEKLY
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))    # domain.js REVIEW_WEEKLY








def _out(row: Any) -> WeeklyReportResponse:
    """
    Fungsi pembantu untuk memetakan row laporan mingguan dari database ke skema WeeklyReportResponse.

    Args:
        row (Any): Row data laporan mingguan dari database.

    Returns:
        WeeklyReportResponse: Respons model laporan mingguan.
    """
    return WeeklyReportResponse(**(row if isinstance(row, dict) else row._mapping))


@router.get("", response_model=list[WeeklyReportResponse])
async def list_weeks(access: PlanAccess = _VIEW_ACCESS, weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> list[WeeklyReportResponse]:
    """
    Mengambil daftar laporan mingguan untuk sebuah SK (GET).

    Path Parameters:
    - plan_id (tersirat via router prefix): ID dari work plan.

    Returns:
    - list[WeeklyReportResponse]: Daftar laporan mingguan.
    """
    # Menggunakan Dependency Injection untuk memastikan hak akses (_VIEW_ACCESS) dan service laporan mingguan
    # Memanggil service layer untuk mengambil data minggu
    return [_out(row) for row in await weekly_report_service.list_weeks(access)]


@router.put("/{week}", response_model=WeeklyReportResponse)
async def save_weekly(week: int, data: WeeklyReportRequest, access: PlanAccess = _LEADER_ACCESS,
                      weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> WeeklyReportResponse:
    """
    Menyimpan draf laporan mingguan (PUT). (domain.js SAVE_WEEKLY)

    Path Parameters:
    - week (int): Minggu ke-berapa.

    Request Body:
    - data (WeeklyReportRequest): Data isi laporan dan kendala.

    Returns:
    - WeeklyReportResponse: Data laporan mingguan yang berhasil disimpan.
    """
    # Dependency Injection untuk memastikan hak akses Leader (_LEADER_ACCESS)
    # Memanggil Service layer untuk operasi penyimpanan data laporan mingguan
    return _out(await weekly_report_service.save_weekly(access, week, data.body, data.obstacle))


@router.post("/{week}/submit", response_model=WeeklyReportResponse)
async def submit_weekly(week: int, access: PlanAccess = _LEADER_ACCESS,
                        weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> WeeklyReportResponse:
    """
    Mengajukan laporan mingguan agar bisa ditinjau (POST). (domain.js SUBMIT_WEEKLY)

    Path Parameters:
    - week (int): Minggu ke-berapa.

    Returns:
    - WeeklyReportResponse: Status laporan mingguan yang baru.
    """
    # Memastikan hak akses sebagai Leader menggunakan Dependency Injection
    # Melakukan pemanggilan submit di layer Service
    return _out(await weekly_report_service.submit_weekly(access, week))


@router.post("/{week}/review", response_model=WeeklyReportResponse)
async def review_weekly(week: int, data: WeeklyReviewRequest, access: PlanAccess = _PM_UNIT_ACCESS,
                        weekly_report_service: WeeklyReportService = Depends(get_weekly_report_service)) -> WeeklyReportResponse:
    """
    Meninjau laporan mingguan (PM Unit) untuk disetujui atau ditolak (POST). (domain.js REVIEW_WEEKLY)

    Path Parameters:
    - week (int): Minggu ke-berapa.

    Request Body:
    - data (WeeklyReviewRequest): Keputusan (decision) dan catatan.

    Returns:
    - WeeklyReportResponse: Status laporan mingguan yang baru.
    """
    # Dependency Injection untuk hak akses _PM_UNIT_ACCESS dan WeeklyReportService
    # Meneruskan data keputusan review (decision dan note) ke Service layer
    return _out(await weekly_report_service.review_weekly(access, week, data.decision, data.note))
