"""
Dokumen SK, tanda tangan ber-QR, PDF, dan verifikasi publik (fase 6, dok 05 §3.9).
Verifikasi `/verify/{token}` PUBLIK (tanpa login) dan dibatasi 30 permintaan/menit per IP (dok 05 §5).
"""
import time
from collections import defaultdict, deque
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response

from app.api.deps import get_current_user, get_public_signature_service, get_signature_service, plan_access
from app.core.errors import AppError
from app.core.security import CurrentUser
from app.schemas.signature import PlanDocumentOut, RevokeRequest, SignatureOut, VerifyOut
from app.services.access_service import PlanAccess, PlanNeed
from app.services.pdf_service import html_to_pdf, render_plan_document_html
from app.services.signature_service import SignatureService

plan_documents_router = APIRouter(prefix="/work-plans/{plan_id}/documents", tags=["Documents & Signatures"])
router = APIRouter(tags=["Documents & Signatures"])
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))

VERIFY_LIMIT, VERIFY_WINDOW = 30, 60.0
_verify_hits: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit(ip: str) -> None:
    """30/menit per IP (dok 05 §5) — mencegah penyisiran token. Per proses; cukup untuk satu instans API."""
    now, hits = time.monotonic(), _verify_hits[ip]
    while hits and now - hits[0] > VERIFY_WINDOW:
        hits.popleft()
    if len(hits) >= VERIFY_LIMIT:
        raise AppError("TOO_MANY_REQUESTS", "Terlalu sering memeriksa. Coba lagi sebentar lagi.", status=429)
    hits.append(now)










def _rows(rows: list[Any], model: Any) -> list[Any]:
    """
    Fungsi pembantu untuk memetakan kumpulan baris (row) database ke skema tertentu.

    Args:
        rows (list[Any]): Daftar row dari database.
        model (Any): Skema Pydantic tujuan (seperti SignatureOut).

    Returns:
        list[Any]: Daftar model yang sudah dipetakan.
    """
    return [model(**row._mapping) for row in rows]


@plan_documents_router.get("", response_model=list[PlanDocumentOut])
async def list_plan_documents(access: PlanAccess = _VIEW_ACCESS,
                              signature_service: SignatureService = Depends(get_signature_service)) -> list[PlanDocumentOut]:
    """
    Dok 05 §3.3: SK, revisi, dan adendum beserta jumlah tanda tangan yang berlaku (GET).

    Path Parameters:
    - plan_id (tersirat via router prefix): ID dari work plan.

    Returns:
    - list[PlanDocumentOut]: Daftar dokumen rencana kerja.
    """
    # Menggunakan Dependency Injection untuk memeriksa hak akses VIEW pada plan
    # Menggunakan Dependency Injection untuk instansiasi SignatureService
    # Memanggil method layer Service untuk mengambil daftar dokumen
    return _rows(await signature_service.list_plan_documents(access.plan.id), PlanDocumentOut)


@router.get("/documents/{document_id}/signatures", response_model=list[SignatureOut])
async def list_signatures(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                          signature_service: SignatureService = Depends(get_signature_service)) -> list[SignatureOut]:
    """
    Mengambil daftar tanda tangan untuk sebuah dokumen (GET).

    Path Parameters:
    - document_id (UUID): ID dari dokumen yang tanda tangannya ingin diambil.

    Returns:
    - list[SignatureOut]: Daftar tanda tangan yang terkait dengan dokumen.
    """
    # Menggunakan Dependency Injection untuk mendapatkan user saat ini
    # Menggunakan Dependency Injection untuk mendapatkan SignatureService
    # Memetakan pemanggilan ke layer Service untuk mengambil daftar tanda tangan
    return _rows(await signature_service.list_signatures(current_user, document_id), SignatureOut)


@router.get("/documents/{document_id}/pdf", response_class=Response)
async def document_pdf(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                       signature_service: SignatureService = Depends(get_signature_service)) -> Response:
    """
    Mengunduh dokumen dalam format PDF bertanda tangan + QR verifikasi (dok 05 §3.9) (GET).
    Render berat → threadpool (CLAUDE.md).

    Path Parameters:
    - document_id (UUID): ID dokumen.

    Returns:
    - Response: File PDF dari dokumen bersangkutan.
    """
    # Inject user saat ini dan SignatureService
    # Memanggil Service untuk mendapatkan data dokumen dan tanda tangannya
    document, signatures = await signature_service.document_with_qr(current_user, document_id)
    html = render_plan_document_html(document, signatures)
    pdf = await run_in_threadpool(html_to_pdf, html)
    filename = f"{document.number}-v{document.version}.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/documents/{document_id}/html", response_class=HTMLResponse)
async def document_html(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                        signature_service: SignatureService = Depends(get_signature_service)) -> HTMLResponse:
    """
    Mendapatkan representasi HTML dari dokumen, sama persis dengan PDF (templat A4 + TTD + QR) (GET).
    Untuk penampil di web & HP ("Tinjau SK").

    Path Parameters:
    - document_id (UUID): ID dari dokumen.

    Returns:
    - HTMLResponse: Konten HTML dokumen.
    """
    # Menggunakan Dependency Injection untuk user dan service
    # Memanggil SignatureService untuk memperoleh data dokumen beserta QR code
    document, signatures = await signature_service.document_with_qr(current_user, document_id)
    return HTMLResponse(render_plan_document_html(document, signatures))


@router.post("/signatures/{signature_id}/revoke")
async def revoke_signature(signature_id: UUID, data: RevokeRequest,
                           current_user: CurrentUser = Depends(get_current_user),
                           signature_service: SignatureService = Depends(get_signature_service)) -> dict[str, str]:
    """
    Pencabutan tanda tangan beserta alasan (PM unit/OPS SK tersebut) (POST).
    Tercatat di audit. (P6-6)

    Path Parameters:
    - signature_id (UUID): ID dari tanda tangan yang akan dicabut.

    Request Body:
    - data (RevokeRequest): Alasan pencabutan.

    Returns:
    - dict[str, str]: Pesan sukses.
    """
    # Menggunakan Dependency Injection untuk mendapatkan data user saat ini dan SignatureService
    # Memanggil Service layer untuk proses pencabutan tanda tangan
    await signature_service.revoke_signature(current_user, signature_id, data.reason)
    return {"message": "Tanda tangan dicabut."}


@router.get("/verify/{token:path}", response_model=VerifyOut)
async def verify_signature(token: str, request: Request, public_signature_service: SignatureService = Depends(get_public_signature_service)) -> VerifyOut:
    """
    Memverifikasi tanda tangan berdasarkan token dari hasil pemindaian QR (PUBLIK) (GET).
    Hanya mengembalikan data yang perlu dilihat pemverifikasi.

    Path Parameters:
    - token (str): Token yang diperoleh dari QR code.

    Returns:
    - VerifyOut: Data verifikasi tanda tangan publik.
    """
    # Menggunakan Dependency Injection (get_public_signature_service) yang digunakan untuk akses publik
    _rate_limit(request.client.host if request.client else "unknown")
    # Memanggil method Service layer untuk verifikasi publik
    row = await public_signature_service.verify(token)
    data = dict(row._mapping)
    data["state"] = str(data["state"])
    data["signer_role"] = str(data["signer_role"]) if data.get("signer_role") else None
    return VerifyOut(**data)


