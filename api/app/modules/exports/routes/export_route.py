"""
app/modules/exports/routes/export_route.py

Rute ekspor dokumen resmi (Milestone 8, docs/35 §8). Setiap ekspor tercatat di `document_template_export` dan bisa
diunduh ulang lewat `/exports/{export_id}/file`.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import IdempotencyGuard, get_current_user, idempotency_guard, require_permission
from app.core.permissions import Permission
from app.core.rate_limit import GROUP_UPLOAD, rate_limit
from app.core.security import CurrentUser
from app.modules.exports.controllers.export_controller import ExportController
from app.modules.exports.schemas.export_schema import (
    CompletionExportRequest,
    DailyReportExportRequest,
    ExportOut,
    MonthlyExportRequest,
    PeriodicExportRequest,
    ReportFormat,
    SurveyLogoOut,
    TeamWeekExportRequest,
)
from app.shared.documents import branding
from app.shared.documents.branding import LogoRole

router = APIRouter(prefix="/exports", tags=["Ekspor Dokumen"])
_FILE: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/octet-stream": {}}, "description": "Berkas dokumen"}
}
_PM = Depends(require_permission(Permission.CREATE_PLAN))


@router.post("/work-completions/{completion_id}", response_class=Response, responses=_FILE)
async def export_work_completion(
    completion_id: UUID,
    body: CompletionExportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> Response:
    """Berita acara serah terima, laporan survei, surat tugas, atau laporan kemajuan: PDF, Word, atau PowerPoint
    (`export_format`; kosong = bawaan jenisnya) dengan isi setara. Juga: berita acara resmi ber-QR (.pdf) dan
    rincian volume dan biaya (.xlsx). Mendukung Idempotency-Key; klik ganda mengembalikan dokumen yang sama."""
    return await controller.idempotent(
        current_user, idem, lambda: controller.export_completion(current_user, completion_id, body))


@router.get("/surveys/{task_id}/preview", response_class=Response, responses=_FILE)
async def preview_survey(
    task_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
) -> Response:
    """Pratinjau laporan survei (PDF; .docx bila konverter tak tersedia) — ketua tim & PM, juga sebelum dikirim.
    Tidak disimpan ke registri ekspor."""
    return await controller.preview_survey(current_user, task_id)


@router.get("/survey-logos", response_model=list[SurveyLogoOut])
def survey_logos(current_user: CurrentUser = _PM, controller: ExportController = Depends()) -> list[SurveyLogoOut]:
    """Logo kop laporan survei (perusahaan & klien) beserta ukuran bakunya."""
    return controller.survey_logos(current_user)


@router.get("/survey-logos/{role}", response_class=Response, responses=_FILE)
def survey_logo_image(role: LogoRole, current_user: CurrentUser = _PM,
                      controller: ExportController = Depends()) -> Response:
    """Gambar logo pengganti (404 bila masih memakai logo bawaan template)."""
    return controller.survey_logo_image(current_user, role)


@router.put(
    "/survey-logos/{role}",
    response_model=list[SurveyLogoOut],
    dependencies=[Depends(rate_limit(GROUP_UPLOAD))],
)
async def set_survey_logo(role: LogoRole, file: UploadFile = File(...), current_user: CurrentUser = _PM,
                          controller: ExportController = Depends()) -> list[SurveyLogoOut]:
    """Ganti logo kop: gambar dipasang utuh (rasio dijaga) ke kotak ukuran baku di setiap template."""
    return controller.set_survey_logo(current_user, role, await file.read(branding.MAX_UPLOAD + 1))


@router.delete("/survey-logos/{role}", response_model=list[SurveyLogoOut])
def reset_survey_logo(role: LogoRole, current_user: CurrentUser = _PM,
                      controller: ExportController = Depends()) -> list[SurveyLogoOut]:
    """Kembali ke logo bawaan template."""
    return controller.reset_survey_logo(current_user, role)


@router.post("/surveys/{task_id}", response_class=Response, responses=_FILE)
async def export_survey(
    task_id: UUID,
    export_format: ReportFormat | None = Query(None, description="PDF, WORD_DOCX, atau PPTX; kosong = Word"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> Response:
    """Laporan survei ACS/CCTV format baku (docs/37) dalam PDF, Word (bawaan), atau PowerPoint; tersedia setelah
    survei dikirim. Mendukung Idempotency-Key; klik ganda mengembalikan dokumen yang sama."""
    return await controller.idempotent(
        current_user, idem, lambda: controller.export_survey(current_user, task_id, export_format))


@router.get("/work-completions/{completion_id}", response_model=list[ExportOut])
async def list_work_completion_exports(
    completion_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
) -> list[ExportOut]:
    """Riwayat dokumen yang pernah dibuat untuk order ini."""
    return await controller.list_for_completion(current_user, completion_id)


@router.post("/periodic", response_class=Response, responses=_FILE)
async def export_periodic(
    body: PeriodicExportRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: ExportController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> Response:
    """Rekap divisi per rentang (maks. 31 hari): jadwal, rincian volume dan biaya, uang makan (.xlsx) atau slide
    mingguan (.pptx). Mendukung Idempotency-Key."""
    return await controller.idempotent(current_user, idem, lambda: controller.export_periodic(current_user, body))


@router.post("/monthly", response_class=Response, responses=_FILE)
async def export_monthly(
    body: MonthlyExportRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: ExportController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> Response:
    """Laporan bulanan divisi (satu bulan kalender): jadwal tim, rincian material, dan uang makan dalam Word
    (bawaan), PDF, atau PowerPoint. Izin sama dengan rekap divisi (PM/OM divisi atau SUPER_ADMIN); divisi di luar
    cakupan: 404. Mendukung Idempotency-Key."""
    return await controller.idempotent(current_user, idem, lambda: controller.export_monthly(current_user, body))


@router.post("/team-week", response_class=Response, responses=_FILE)
async def export_team_week(
    body: TeamWeekExportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> Response:
    """Laporan mingguan tim: semua pekerjaan tim 7 hari (Senin sampai Minggu) — foto, keterangan, status — dalam
    PowerPoint (bawaan), PDF, atau Word. Ketua/anggota tim atau PM/OM divisinya; tim di luar cakupan: 404.
    Mendukung Idempotency-Key."""
    return await controller.idempotent(current_user, idem, lambda: controller.export_team_week(current_user, body))


@router.post("/daily-report", response_class=Response, responses=_FILE)
async def export_daily_report(
    body: DailyReportExportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
    idem: IdempotencyGuard = Depends(idempotency_guard),
) -> Response:
    """Laporan harian satu jadwal: header jadwal, tim, item + status/catatan/alasan tunda, foto, laporan ketua,
    dalam Word (bawaan), PDF, atau PowerPoint. Ketua/anggota tim atau PM/OM divisi (jadwal yang sudah dirilis).
    Mendukung Idempotency-Key."""
    return await controller.idempotent(current_user, idem, lambda: controller.export_daily_report(current_user, body))


@router.get("/periodic", response_model=list[ExportOut])
async def list_periodic_exports(
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    controller: ExportController = Depends(),
) -> list[ExportOut]:
    """Rekap periodik: OM & SUPER_ADMIN melihat semua, PM miliknya sendiri."""
    return await controller.list_periodic(current_user)


@router.get("/{export_id}/file", response_class=Response, responses=_FILE)
async def download_export(
    export_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: ExportController = Depends(),
) -> Response:
    """Unduh ulang dokumen dari registri (hak sama dengan saat membuatnya)."""
    return await controller.download(current_user, export_id)
