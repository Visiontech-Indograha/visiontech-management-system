"""
Transisi SK: terbitkan (PM unit/OPS), terima & mulai (ketua menurut SK) — dijaga `plan_access`
(V-07). Tipis (dok 12 §2): aturan di services/plan_transition_service.py, SQL di
crud/crud_plan_transition.py.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user, get_plan_transition_service, get_signature_service, plan_access
from app.schemas.plan import WorkPlanResponse
from app.schemas.plan_transition import (
    CompletionRequest,
    FinalReportOut,
    FinalReportSignatureOut,
    TransitionRequest,
)
from app.services.access_service import PlanAccess, PlanNeed, ensure_same_org
from app.services.pdf_service import html_to_pdf, render_final_report_html
from app.services.plan_transition_service import PlanTransitionService
from app.services.signature_service import SignatureService

router = APIRouter(prefix="/work-plans/{plan_id}", tags=["Work Plan Transitions"])
_LEADER_ACCESS = Depends(plan_access(PlanNeed.LEADER))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_PM_UNIT_ANY_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT, archived=None))  # aktif maupun terarsip
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))






@router.get("/completion/signatures", response_model=list[FinalReportSignatureOut])
async def get_final_report_signatures(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    signature_service: SignatureService = Depends(get_signature_service),
) -> list[FinalReportSignatureOut]:
    """
    Mengambil daftar tanda tangan laporan akhir (GET).
    Tanda tangan laporan akhir (ketua = ISSUER, pemeriksa = APPROVER), R-19.
    
    Path Parameters:
    - plan_id (UUID): ID rencana kerja.
    
    Returns:
    - list[FinalReportSignatureOut]: Daftar tanda tangan.
    """
    # Menggunakan Dependency Injection untuk akses VIEW (_VIEW_ACCESS)
    # Memanggil layanan SignatureService
    rows = await signature_service.final_report_signatures(plan_id)
    return [FinalReportSignatureOut(**r._mapping) for r in rows]


@router.get("/completion/pdf", response_class=Response)
async def get_final_report_pdf(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    signature_service: SignatureService = Depends(get_signature_service),
) -> Response:
    """
    Mengunduh PDF laporan akhir ber-QR (GET).
    P6-4, UAT langkah 10. Hanya setelah disetujui (409).
    Render HTML ke PDF berjalan di background threadpool.
    
    Path Parameters:
    - plan_id (UUID): ID rencana kerja.
    
    Returns:
    - Response: File PDF biner.
    """
    # Dependency Injection untuk hak akses dan SignatureService
    # PDF rendering dilakukan dalam threadpool agar tidak memblok event loop
    plan, signatures = await signature_service.final_report_with_qr(access.user, plan_id)
    pdf = await run_in_threadpool(html_to_pdf, render_final_report_html(plan, signatures))
    filename = f"{plan.number}-laporan-akhir.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/completion", response_model=FinalReportOut | None)
async def get_final_report(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> FinalReportOut | None:
    """
    Mengambil data laporan akhir SK (GET).
    Laporan akhir SK — dibaca PM sebelum menyetujui/mengembalikan, dan untuk mode presentasi.
    null bila belum pernah diajukan; SK tak terlihat → 404 (penjaga VIEW).
    
    Path Parameters:
    - plan_id (UUID): ID dari SK terkait.
    
    Returns:
    - FinalReportOut | None: Detail final report jika ada.
    """
    # Memeriksa hak akses read (_VIEW_ACCESS) via Dependency Injection
    # Menggunakan PlanTransitionService untuk fetch data
    row = await plan_transition_service.final_report(plan_id)
    return FinalReportOut(**row._mapping) if row else None




def _response(row: Any) -> WorkPlanResponse:
    """
    Fungsi pembantu untuk memetakan row data SK dari database ke skema WorkPlanResponse.
    
    Args:
        row (Any): Row data Surat Kerja.
        
    Returns:
        WorkPlanResponse: Respons model Surat Kerja.
    """
    return WorkPlanResponse(**row._mapping)


@router.post("/publish", response_model=WorkPlanResponse)
async def publish_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    PM menerbitkan SK (POST).
    Status SK berubah menjadi PUBLISHED.
    
    Path Parameters:
    - plan_id (UUID): ID SK.
    
    Request Body:
    - data (TransitionRequest): Versi baris dan data transisi lainnya.
    
    Returns:
    - WorkPlanResponse: Rencana kerja terbaru.
    """
    # PM_UNIT_ACCESS diinjeksikan untuk validasi hak akses
    # Proses publikasi ditangani oleh PlanTransitionService
    plan = await plan_transition_service.publish(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/accept", response_model=WorkPlanResponse)
async def accept_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Ketua menerima SK yang diterbitkan PM (POST).
    Status SK berubah menjadi ACCEPTED.
    
    Path Parameters:
    - plan_id (UUID): ID rencana kerja.
    
    Request Body:
    - data (TransitionRequest): Versi baris (row version).
    
    Returns:
    - WorkPlanResponse: Rencana kerja terbaru.
    """
    # Memeriksa hak akses ketua (_LEADER_ACCESS)
    # Memanggil PlanTransitionService untuk menerima (accept) SK
    plan = await plan_transition_service.accept(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)


@router.post("/appeal", response_model=WorkPlanResponse)
async def appeal_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Ketua mengajukan banding atas SK yang terbit (POST).
    (domain.js APPEAL, V-20).
    Status SK berubah menjadi APPEALED.
    
    Path Parameters:
    - plan_id (UUID): ID SK.
    
    Request Body:
    - data (TransitionRequest): Data banding beserta alasannya.
    
    Returns:
    - WorkPlanResponse: Rencana kerja dengan status banding.
    """
    # Dependency Injection memastikan aktor adalah LEADER
    # Layer Service memproses banding (appeal)
    plan = await plan_transition_service.appeal(plan_id, access.user.organization_id, access.user.user_id,
                                     data.row_version, data.reason)
    return _response(plan)


@router.post("/revise", response_model=WorkPlanResponse)
async def revise_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    PM membuka revisi draf dari SK yang dibanding (POST).
    (domain.js REVISE, V-20).
    Status SK kembali menjadi DRAFT_REV.
    
    Path Parameters:
    - plan_id (UUID): ID dari SK yang akan direvisi.
    
    Request Body:
    - data (TransitionRequest): Data permintaan transisi (row version).
    
    Returns:
    - WorkPlanResponse: Rencana kerja dengan status DRAFT_REV.
    """
    # Menggunakan Dependency Injection (_PM_UNIT_ACCESS)
    # Memanggil method revise dari Service layer
    plan = await plan_transition_service.revise(plan_id, access.user.organization_id, data.row_version)
    return _response(plan)


@router.post("/cancel", response_model=WorkPlanResponse)
async def cancel_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Membatalkan rencana kerja (POST).
    (domain.js CANCEL_PLAN, V-21).
    Status SK menjadi CANCELLED.
    
    Path Parameters:
    - plan_id (UUID): ID dari SK.
    
    Request Body:
    - data (TransitionRequest): Data dan alasan pembatalan.
    
    Returns:
    - WorkPlanResponse: Rencana kerja yang dibatalkan.
    """
    # Verifikasi PM_UNIT melalui Dependency Injection
    # Mengirim instruksi pembatalan ke Service layer
    return _response(await plan_transition_service.cancel_plan(plan_id, access.user.organization_id,
                                                     data.row_version, data.reason))


@router.post("/archive", response_model=WorkPlanResponse)
async def archive_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Mengarsipkan (menghapus secara logis) draf SK (POST).
    (domain.js DELETE_PLAN, V-21): arsip draf — soft delete, riwayat tetap ada.
    
    Path Parameters:
    - plan_id (UUID): ID SK.
    
    Request Body:
    - data (TransitionRequest): Alasan pengarsipan.
    
    Returns:
    - WorkPlanResponse: Rencana kerja yang diarsipkan.
    """
    # Memeriksa izin penghapusan (PM_UNIT) melalui Dependency Injection
    # Memanggil fungsi delete_plan di layer Service (soft delete)
    return _response(await plan_transition_service.delete_plan(plan_id, access.user.organization_id, access.user.user_id,
                                                    data.row_version, data.reason))


@router.post("/restore", response_model=WorkPlanResponse)
async def restore_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ANY_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Memulihkan draf SK terarsip (POST).
    (domain.js RESTORE_PLAN, V-21).
    
    Path Parameters:
    - plan_id (UUID): ID dari SK yang akan dipulihkan.
    
    Request Body:
    - data (TransitionRequest): Data baris transisi.
    
    Returns:
    - WorkPlanResponse: Rencana kerja yang berhasil dipulihkan.
    """
    # Memeriksa PM_UNIT_ANY_ACCESS untuk memungkinkan pemulihan dari arsip
    # Memanggil PlanTransitionService (restore_plan)
    return _response(await plan_transition_service.restore_plan(plan_id, access.user.organization_id, data.row_version))


@router.post("/start", response_model=WorkPlanResponse)
async def start_plan(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Ketua memulai pekerjaan berdasarkan SK yang telah diterima (POST).
    Status SK berubah menjadi IN_PROGRESS.
    
    Path Parameters:
    - plan_id (UUID): ID SK.
    
    Request Body:
    - data (TransitionRequest): Versi data row.
    
    Returns:
    - WorkPlanResponse: Rencana kerja dengan status berjalan.
    """
    # Hak akses ketua tim dijamin oleh Dependency Injection
    # Mengeksekusi transisi start lewat Service layer
    plan = await plan_transition_service.start(plan_id, access.user.organization_id, access.user.user_id, data.row_version)
    return _response(plan)




@router.post("/request-completion", response_model=WorkPlanResponse)
async def request_completion(
    plan_id: UUID,
    data: CompletionRequest,
    access: PlanAccess = _LEADER_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    Ketua menyerahkan laporan akhir (POST).
    (domain.js REQUEST_COMPLETE, V-26): status menjadi COMPLETION_REVIEW.
    
    Path Parameters:
    - plan_id (UUID): ID dari rencana kerja.
    
    Request Body:
    - data (CompletionRequest): Isi laporan akhir, kendala, dan file bukti (evidence).
    
    Returns:
    - WorkPlanResponse: Rencana kerja yang sedang di-review.
    """
    # Menggunakan Dependency Injection untuk kontrol hak akses LEADER dan db session
    # Memastikan file lampiran dimiliki oleh organisasi yang benar
    await ensure_same_org(db, access.user.organization_id, files=data.evidence_file_ids)
    # Memanggil Service layer untuk mengajukan laporan selesai
    return _response(await plan_transition_service.request_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version,
        data.body, data.obstacle, data.evidence_file_ids))


@router.post("/approve-completion", response_model=WorkPlanResponse)
async def approve_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    PM unit/OPS menutup SK setelah menyetujui laporan akhir (POST).
    (domain.js APPROVE_COMPLETE, V-26): status menjadi COMPLETED.
    
    Path Parameters:
    - plan_id (UUID): ID dari SK.
    
    Request Body:
    - data (TransitionRequest): Data persetujuan.
    
    Returns:
    - WorkPlanResponse: SK yang berstatus COMPLETED.
    """
    # Memeriksa izin dari PM (_PM_UNIT_ACCESS) via Dependency Injection
    # Mengesahkan status selesai melalui layer Service
    return _response(await plan_transition_service.approve_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version, data.reason))


@router.post("/return-completion", response_model=WorkPlanResponse)
async def return_completion(
    plan_id: UUID,
    data: TransitionRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> WorkPlanResponse:
    """
    PM unit/OPS mengembalikan laporan akhir ke ketua (POST).
    (domain.js RETURN_COMPLETE, V-26): status menjadi IN_PROGRESS kembali.
    
    Path Parameters:
    - plan_id (UUID): ID SK terkait.
    
    Request Body:
    - data (TransitionRequest): Data alasan pengembalian laporan.
    
    Returns:
    - WorkPlanResponse: Rencana kerja dikembalikan ke berjalan.
    """
    # Memastikan hak akses level PM (_PM_UNIT_ACCESS)
    # Memerintahkan Service layer untuk menolak penyelesaian dan mengembalikannya ke ketua
    return _response(await plan_transition_service.return_complete(
        plan_id, access.user.organization_id, access.user.user_id, data.row_version, data.reason))
