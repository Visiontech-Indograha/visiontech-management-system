"""
app/modules/signatures/routes/signature_route.py

Rute endpoint HTTP untuk tanda tangan, PDF/HTML, dan verifikasi token publik.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.signatures.controllers.signature_controller import (
    PublicSignatureController,
    SignatureController,
)
from app.modules.signatures.schemas.signature_schema import (
    RevokeRequest,
    SignatureOut,
    VerifyOut,
)

router = APIRouter(tags=["Documents & Signatures"])


@router.get("/documents/{document_id}/signatures", response_model=list[SignatureOut])
async def list_signatures(
    document_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SignatureController = Depends(),
) -> list[SignatureOut]:
    """Mengambil daftar tanda tangan untuk sebuah dokumen."""
    return await controller.handle_list_signatures(current_user, document_id)


@router.get("/documents/{document_id}/pdf", response_class=Response)
async def document_pdf(
    document_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SignatureController = Depends(),
) -> Response:
    """Mengunduh dokumen dalam format PDF bertanda tangan + QR verifikasi."""
    return await controller.handle_document_pdf(current_user, document_id)


@router.get("/documents/{document_id}/html", response_class=HTMLResponse)
async def document_html(
    document_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SignatureController = Depends(),
) -> HTMLResponse:
    """Mendapatkan representasi HTML dari dokumen ber-QR untuk penampil di aplikasi."""
    return await controller.handle_document_html(current_user, document_id)


@router.post("/signatures/{signature_id}/revoke")
async def revoke_signature(
    signature_id: UUID,
    data: RevokeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: SignatureController = Depends(),
) -> dict[str, str]:
    """Pencabutan tanda tangan beserta alasan."""
    return await controller.handle_revoke_signature(current_user, signature_id, data)


@router.get("/verify/{token:path}", response_model=VerifyOut)
async def verify_signature(
    token: str,
    request: Request,
    controller: PublicSignatureController = Depends(),
) -> VerifyOut:
    """Memverifikasi tanda tangan berdasarkan token dari hasil pemindaian QR (PUBLIK)."""
    client_ip = request.client.host if request.client else "unknown"
    return await controller.handle_verify(token, client_ip)
