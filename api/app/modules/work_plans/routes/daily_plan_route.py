"""
app/modules/work_plans/routes/daily_plan_route.py
Rute jadwal harian daily-first (/work-plans): daftar per rentang tanggal (minggu), detail, buat/ubah/salin/hapus,
ajukan → setujui (per hari atau matriks) → mulai → selesai, lampiran, jadwal per order, pencarian lokasi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import daily_access, get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.daily_plan_controller import DailyPlanController
from app.modules.work_plans.schemas.daily_plan_schema import (
    AttachmentsIn,
    BulkApproveIn,
    BulkApproveOut,
    DailyActivateIn,
    DailyBulkIn,
    DailyBulkOut,
    DailyBulkStandbyIn,
    DailyFormOptions,
    DailyPlanCopy,
    DailyPlanCreate,
    DailyPlanDetail,
    DailyPlanOut,
    DailyPlanUpdate,
    DailyStatus,
    GeoResult,
    OrderScheduleOut,
    RecentSiteOut,
    RejectIn,
)
from app.modules.work_plans.schemas.daily_report_schema import (
    DailyReportCreate,
    DailyReportOut,
    WeeklyPresentationOut,
)
from app.modules.work_plans.schemas.weekly_schema import WeeklyMatrixOut
from app.shared.access.access_service import DailyAccess, DailyNeed

router = APIRouter(prefix="/work-plans", tags=["Work Plans (Daily-First)"])
_LOGIN = Depends(get_current_user)
_PLANNER = Depends(require_permission(Permission.CREATE_PLAN))
_VIEW = Depends(daily_access(DailyNeed.VIEW))


@router.get("/form-options", response_model=DailyFormOptions)
async def form_options(current_user: CurrentUser = _PLANNER, controller: DailyPlanController = Depends()
                       ) -> DailyFormOptions:
    """Pilihan divisi, tim, dan order terbuka yang dikelola pengguna."""
    return await controller.handle_form_options(current_user)


@router.get("/weekly", response_model=WeeklyMatrixOut)
async def weekly_matrix(week_start: date = Query(description="Senin awal minggu (YYYY-MM-DD)"),
                        division_id: UUID | None = Query(default=None),
                        current_user: CurrentUser = _PLANNER,
                        controller: DailyPlanController = Depends()) -> WeeklyMatrixOut:
    """Matriks alokasi mingguan: tim × 7 hari (Senin–Minggu) untuk divisi yang dikelola PM/OM. `division_id` opsional
    (kosong = semua divisi yang dikelola). Sel memuat status, jenis (WORK/STANDBY), ringkasan item, dan sisa target
    order."""
    return await controller.handle_weekly(current_user, week_start, division_id)


@router.get("/geo/search", response_model=list[GeoResult])
async def geo_search(q: str = Query(min_length=3, max_length=200), current_user: CurrentUser = _PLANNER,
                     controller: DailyPlanController = Depends()) -> list[GeoResult]:
    """Cari koordinat lokasi site (OpenStreetMap)."""
    return await controller.handle_geo_search(q)


@router.get("/daily/recent-sites", response_model=list[RecentSiteOut])
async def recent_sites(team_id: UUID, limit: int = Query(default=10, ge=1, le=30), current_user: CurrentUser = _PLANNER,
                       controller: DailyPlanController = Depends()) -> list[RecentSiteOut]:
    """Lokasi site yang pernah dipakai tim, terbaru dulu (dipilih ulang di form Jadwal harian)."""
    return await controller.handle_recent_sites(current_user, team_id, limit)


@router.get("/daily", response_model=list[DailyPlanOut])
async def list_daily_plans(
    start: date | None = None,
    end: date | None = None,
    division_id: UUID | None = None,
    team_id: UUID | None = None,
    plan_status: DailyStatus | None = Query(None, alias="status"),
    current_user: CurrentUser = _LOGIN,
    controller: DailyPlanController = Depends(),
) -> list[DailyPlanOut]:
    """Jadwal dalam rentang tanggal (default: minggu ini, Senin–Minggu). PM/OM: divisinya; lapangan: timnya,
    yang sudah disetujui."""
    return await controller.handle_list(current_user, start, end, division_id, team_id, plan_status)


@router.post("/daily", response_model=DailyPlanOut, status_code=status.HTTP_201_CREATED)
async def create_daily_plan(data: DailyPlanCreate, current_user: CurrentUser = _PLANNER,
                            controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """Membuat jadwal harian (DRAFT) untuk satu tim pada satu tanggal."""
    return await controller.handle_create(current_user, data)


@router.post("/daily/bulk", response_model=DailyBulkOut)
async def bulk_create_daily(data: DailyBulkIn, current_user: CurrentUser = _PLANNER,
                            controller: DailyPlanController = Depends()) -> DailyBulkOut:
    """Alokasi massal: banyak tim × banyak tanggal. Sel yang bentrok dilaporkan, tidak membatalkan sel lain."""
    return await controller.handle_bulk_create(current_user, data)


@router.post("/daily/bulk-standby", response_model=DailyBulkOut)
async def bulk_standby_daily(data: DailyBulkStandbyIn, current_user: CurrentUser = _PLANNER,
                             controller: DailyPlanController = Depends()) -> DailyBulkOut:
    """Siaga untuk hari kosong: hanya sel tim tanpa jadwal yang dibuat sebagai siaga (disetujui)."""
    return await controller.handle_bulk_standby(current_user, data)


@router.post("/daily/{daily_plan_id}/activate", response_model=DailyPlanOut)
async def activate_daily_plan(daily_plan_id: UUID, data: DailyActivateIn, current_user: CurrentUser = _PLANNER,
                              controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """Ubah jadwal siaga jadi pekerjaan klien (STANDBY → WORK) dan beri tahu ketua serta anggota tim."""
    return await controller.handle_activate(current_user, daily_plan_id, data)


@router.post("/daily/approve", response_model=BulkApproveOut)
async def bulk_approve(data: BulkApproveIn, current_user: CurrentUser = _PLANNER,
                       controller: DailyPlanController = Depends()) -> BulkApproveOut:
    """Persetujuan matriks: setujui banyak jadwal sekaligus (yang tidak memenuhi syarat dilewati)."""
    return await controller.handle_bulk_approve(current_user, data.daily_plan_ids)


@router.get("/daily/{daily_plan_id}", response_model=DailyPlanDetail)
async def get_daily_plan(daily_plan_id: UUID, access: DailyAccess = _VIEW,
                         controller: DailyPlanController = Depends()) -> DailyPlanDetail:
    """Detail jadwal beserta item & lampirannya."""
    return await controller.handle_detail(daily_plan_id)


@router.put("/daily/{daily_plan_id}", response_model=DailyPlanOut)
async def update_daily_plan(daily_plan_id: UUID, data: DailyPlanUpdate, current_user: CurrentUser = _PLANNER,
                            controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """Mengubah jadwal (DRAFT/SUBMITTED)."""
    return await controller.handle_update(current_user, daily_plan_id, data)


@router.delete("/daily/{daily_plan_id}")
async def delete_daily_plan(daily_plan_id: UUID, current_user: CurrentUser = _PLANNER,
                            controller: DailyPlanController = Depends()) -> dict[str, str]:
    """Menghapus jadwal yang belum disetujui & belum dipakai."""
    return await controller.handle_delete(current_user, daily_plan_id)


@router.post("/daily/{daily_plan_id}/copy", response_model=list[DailyPlanOut], status_code=status.HTTP_201_CREATED)
async def copy_daily_plan(daily_plan_id: UUID, data: DailyPlanCopy, current_user: CurrentUser = _PLANNER,
                          controller: DailyPlanController = Depends()) -> list[DailyPlanOut]:
    """Menyalin lokasi, jam, & tim ke tanggal lain (DRAFT)."""
    return await controller.handle_copy(current_user, daily_plan_id, data.work_dates)


@router.put("/daily/{daily_plan_id}/attachments", response_model=list[UUID])
async def set_attachments(daily_plan_id: UUID, data: AttachmentsIn, current_user: CurrentUser = _PLANNER,
                          controller: DailyPlanController = Depends()) -> list[UUID]:
    """Mengganti lampiran jadwal (gambar kerja, izin kerja, dsb.)."""
    return await controller.handle_attachments(current_user, daily_plan_id, data.file_ids)


@router.post("/daily/{daily_plan_id}/submit", response_model=DailyPlanOut)
async def submit_daily_plan(daily_plan_id: UUID, current_user: CurrentUser = _PLANNER,
                            controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """DRAFT → SUBMITTED."""
    return await controller.handle_transition(current_user, daily_plan_id, "submit")


@router.post("/daily/{daily_plan_id}/approve", response_model=DailyPlanOut)
async def approve_daily_plan(daily_plan_id: UUID, current_user: CurrentUser = _PLANNER,
                             controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """DRAFT/SUBMITTED → APPROVED (dirilis ke tim lapangan)."""
    return await controller.handle_transition(current_user, daily_plan_id, "approve")


@router.post("/daily/{daily_plan_id}/reject", response_model=DailyPlanOut)
async def reject_daily_plan(daily_plan_id: UUID, data: RejectIn, current_user: CurrentUser = _PLANNER,
                            controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """SUBMITTED/APPROVED → DRAFT dengan alasan."""
    return await controller.handle_transition(current_user, daily_plan_id, "reject", data.reason)


@router.post("/daily/{daily_plan_id}/start", response_model=DailyPlanOut)
async def start_daily_plan(daily_plan_id: UUID, current_user: CurrentUser = _LOGIN,
                           controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """Ketua tim memulai pekerjaan hari itu: APPROVED → ONGOING."""
    return await controller.handle_transition(current_user, daily_plan_id, "start")


@router.post("/daily/{daily_plan_id}/complete", response_model=DailyPlanOut)
async def complete_daily_plan(daily_plan_id: UUID, current_user: CurrentUser = _LOGIN,
                              controller: DailyPlanController = Depends()) -> DailyPlanOut:
    """Ketua tim / PM menutup jadwal: ONGOING → COMPLETED."""
    return await controller.handle_transition(current_user, daily_plan_id, "complete")


@router.post(
    "/daily/{daily_plan_id}/report",
    response_model=DailyReportOut,
    status_code=status.HTTP_201_CREATED,
    summary="Kirim atau Perbarui Laporan Harian Ketua Tim",
)
async def submit_daily_report(
    daily_plan_id: UUID,
    data: DailyReportCreate,
    current_user: CurrentUser = _LOGIN,
    controller: DailyPlanController = Depends(),
) -> DailyReportOut:
    """Laporan harian aktif (ringkasan, kendala, foto) oleh ketua tim atau PM/OM."""
    return await controller.handle_submit_report(current_user, daily_plan_id, data)


@router.get(
    "/daily/{daily_plan_id}/report",
    response_model=DailyReportOut,
    summary="Ambil Laporan Harian Tim",
)
async def get_daily_report(
    daily_plan_id: UUID,
    current_user: CurrentUser = _LOGIN,
    controller: DailyPlanController = Depends(),
) -> DailyReportOut:
    """Detail laporan harian untuk jadwal kerja harian."""
    return await controller.handle_get_report(current_user, daily_plan_id)


@router.get("/orders/{completion_id}/schedule", response_model=OrderScheduleOut)
async def order_schedule(completion_id: UUID, current_user: CurrentUser = _LOGIN,
                         controller: DailyPlanController = Depends()) -> OrderScheduleOut:
    """Jadwal harian yang memuat item order klien ini (proyek multi-minggu) + ringkasan target order."""
    return await controller.handle_order_schedule(current_user, completion_id)


@router.get("/teams/{team_id}/weekly-presentation", response_model=WeeklyPresentationOut)
async def get_team_weekly_presentation(
    team_id: UUID,
    meeting_date: date = Query(..., description="Tanggal pertemuan evaluasi hari Sabtu"),
    current_user: CurrentUser = _LOGIN,
    controller: DailyPlanController = Depends(),
) -> WeeklyPresentationOut:
    """Rekapitulasi presentasi laporan harian selama satu minggu untuk setiap tim pada pertemuan hari Sabtu."""
    return await controller.handle_weekly_presentation(current_user, team_id, meeting_date)

