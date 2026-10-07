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
    """
    Mendapatkan daftar laporan anggota untuk satu hari tertentu (GET).
    Laporan anggota satu hari — dibaca ketua untuk disusun, dan PM saat memeriksa.

    Path Parameters:
    - day_id (UUID): ID dari hari bersangkutan.

    Returns:
    - list[MemberReportOut]: Daftar laporan anggota di hari tersebut.
    """
    # Menggunakan Dependency Injection untuk kontrol hak akses level hari (_DAY_VIEW)
    # Memanggil MemberReportService untuk mengambil seluruh laporan harian anggota
    return [MemberReportOut(**r._mapping) for r in await member_report_service.list_for_day(day_id)]


@router.get("/days/{day_id}/member-report", response_model=MemberReportOut | None)
async def my_member_report(day_id: UUID, access: PlanAccess = _DAY_MEMBER,
                           member_report_service: MemberReportService = Depends(get_member_report_service),
                           ) -> MemberReportOut | None:
    """
    Mengambil draf laporan harian milik anggota itu sendiri (GET).

    Path Parameters:
    - day_id (UUID): ID dari hari bersangkutan.

    Returns:
    - MemberReportOut | None: Detail laporan atau null jika belum ada.
    """
    # Menggunakan Dependency Injection untuk menjamin pengguna bertindak sebagai _DAY_MEMBER
    # Memanggil MemberReportService (mine) untuk mendapatkan laporan khusus anggota yang login
    row = await member_report_service.mine(access, day_id)
    return MemberReportOut(**row._mapping) if row else None


@router.put("/days/{day_id}/member-report", response_model=MemberReportOut)
async def save_member_report(day_id: UUID, data: MemberReportIn, access: PlanAccess = _DAY_MEMBER,
                             member_report_service: MemberReportService = Depends(get_member_report_service),
                             ) -> MemberReportOut:
    """
    Menyimpan draf laporan harian dari seorang anggota (PUT).

    Path Parameters:
    - day_id (UUID): ID hari.

    Request Body:
    - data (MemberReportIn): Isi laporan, kendala, dan file bukti.

    Returns:
    - MemberReportOut: Data laporan yang berhasil disimpan.
    """
    # Memastikan hak akses anggota (_DAY_MEMBER) via Dependency Injection
    # Mengirim data laporan ke Service layer
    row = await member_report_service.save(access, day_id, data.body, data.obstacle, data.evidence_file_ids)
    return MemberReportOut(**row._mapping)


@router.post("/days/{day_id}/member-report/send", response_model=MemberReportOut)
async def send_member_report(day_id: UUID, access: PlanAccess = _DAY_MEMBER,
                             member_report_service: MemberReportService = Depends(get_member_report_service),
                             ) -> MemberReportOut:
    """
    Anggota mengirim laporannya ke ketua tim (POST).
    (Notifikasi ke ketua).

    Path Parameters:
    - day_id (UUID): ID dari hari bersangkutan.

    Returns:
    - MemberReportOut: Laporan yang dikirim dengan status terbaru.
    """
    # Inject izin _DAY_MEMBER dan MemberReportService
    # Meneruskan instruksi kirim (send) ke Service layer
    row = await member_report_service.send(access, day_id)
    return MemberReportOut(**row._mapping)


@router.get("/days/{day_id}/report/html", response_class=HTMLResponse)
async def daily_report_html(day_id: UUID, access: PlanAccess = _DAY_VIEW,
                            member_report_service: MemberReportService = Depends(get_member_report_service),
                            ) -> HTMLResponse:
    """
    Mendapatkan dokumen A4 laporan harian dalam format HTML (GET).
    Isi: ketua + laporan anggota + pemeriksaan PM.

    Path Parameters:
    - day_id (UUID): ID hari kerja.

    Returns:
    - HTMLResponse: Dokumen laporan harian.
    """
    # Menggunakan Dependency Injection untuk kontrol hak akses baca level hari (_DAY_VIEW)
    # Memanggil Service layer untuk di-render menjadi HTML
    return HTMLResponse(await member_report_service.daily_report_html(access, day_id))


@router.get("/weekly/{week}/report/html", response_class=HTMLResponse)
async def weekly_report_html(week: int, access: PlanAccess = _VIEW,
                             member_report_service: MemberReportService = Depends(get_member_report_service),
                             ) -> HTMLResponse:
    """
    Mendapatkan dokumen laporan mingguan dalam format HTML (GET).

    Path Parameters:
    - week (int): Minggu ke-berapa.

    Returns:
    - HTMLResponse: Laporan mingguan.
    """
    # Hak akses tingkat VIEW (_VIEW) dipastikan via Dependency Injection
    # Memanggil Service layer (MemberReportService)
    return HTMLResponse(await member_report_service.weekly_report_html(access, f"Laporan Mingguan {week}"))
