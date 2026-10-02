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
    return [model(**row._mapping) for row in rows]


@plan_documents_router.get("", response_model=list[PlanDocumentOut])
async def list_plan_documents(access: PlanAccess = _VIEW_ACCESS,
                              signature_service: SignatureService = Depends(get_signature_service)) -> list[PlanDocumentOut]:
    """Dok 05 §3.3: SK, revisi, dan adendum beserta jumlah tanda tangan yang berlaku."""
    return _rows(await signature_service.list_plan_documents(access.plan.id), PlanDocumentOut)


@router.get("/documents/{document_id}/signatures", response_model=list[SignatureOut])
async def list_signatures(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                          signature_service: SignatureService = Depends(get_signature_service)) -> list[SignatureOut]:
    return _rows(await signature_service.list_signatures(current_user, document_id), SignatureOut)


@router.get("/documents/{document_id}/pdf", response_class=Response)
async def document_pdf(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                       signature_service: SignatureService = Depends(get_signature_service)) -> Response:
    """PDF bertanda tangan + QR verifikasi (dok 05 §3.9). Render berat → threadpool (CLAUDE.md)."""
    document, signatures = await signature_service.document_with_qr(current_user, document_id)
    html = render_plan_document_html(document, signatures)
    pdf = await run_in_threadpool(html_to_pdf, html)
    filename = f"{document.number}-v{document.version}.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/documents/{document_id}/html", response_class=HTMLResponse)
async def document_html(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                        signature_service: SignatureService = Depends(get_signature_service)) -> HTMLResponse:
    """Isi yang sama persis dengan PDF (templat A4 + TTD + QR) — untuk penampil di web & HP ("Tinjau SK")."""
    document, signatures = await signature_service.document_with_qr(current_user, document_id)
    return HTMLResponse(render_plan_document_html(document, signatures))


@router.post("/signatures/{signature_id}/revoke")
async def revoke_signature(signature_id: UUID, data: RevokeRequest,
                           current_user: CurrentUser = Depends(get_current_user),
                           signature_service: SignatureService = Depends(get_signature_service)) -> dict[str, str]:
    """P6-6: pencabutan beserta alasan (PM unit/OPS SK tersebut); tercatat di audit."""
    await signature_service.revoke_signature(current_user, signature_id, data.reason)
    return {"message": "Tanda tangan dicabut."}


@router.get("/verify/{token:path}", response_model=VerifyOut)
async def verify_signature(token: str, request: Request, public_signature_service: SignatureService = Depends(get_public_signature_service)) -> VerifyOut:
    """PUBLIK: hasil pemindaian QR — hanya data yang perlu dilihat pemverifikasi (db/04 verify_signature_qr)."""
    _rate_limit(request.client.host if request.client else "unknown")
    row = await public_signature_service.verify(token)
    data = dict(row._mapping)
    data["state"] = str(data["state"])
    data["signer_role"] = str(data["signer_role"]) if data.get("signer_role") else None
    return VerifyOut(**data)


