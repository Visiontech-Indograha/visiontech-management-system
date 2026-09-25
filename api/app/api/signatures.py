"""
Dokumen SK, tanda tangan ber-QR, PDF, dan verifikasi publik (fase 6, dok 05 §3.9).
Verifikasi `/verify/{token}` PUBLIK (tanpa login) dan dibatasi 30 permintaan/menit per IP (dok 05 §5).
"""
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db, get_db_with_user
from app.api.guards import PlanAccess, PlanNeed, plan_access
from app.core.errors import AppError
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


class PlanDocumentOut(BaseModel):
    id: str
    kind: str
    version: int
    number: str
    status: str
    reason: str | None
    issued_at: datetime
    accepted_at: datetime | None
    sha256: str
    signature_count: int


class SignatureOut(BaseModel):
    id: str
    serial_number: str
    signer_name: str
    signer_position: str
    signer_unit: str | None
    signer_role: str
    signed_at: datetime
    signature_alg: str
    kid: str
    document_sha256_hex: str
    revoked_at: datetime | None
    revoked_reason: str | None


class RevokeRequest(BaseModel):
    reason: str


class VerifyOut(BaseModel):
    state: str
    serial_number: str | None
    signer_name: str | None
    signer_position: str | None
    signer_unit: str | None
    signer_role: str | None
    document_number: str | None
    document_title: str | None
    signed_at: datetime | None
    key_id: str | None
    algorithm: str | None
    document_sha256_hex: str | None
    note: str | None


def _rows(rows: list[Any], model: Any) -> list[Any]:
    return [model(**row._mapping) for row in rows]


@plan_documents_router.get("", response_model=list[PlanDocumentOut])
async def list_plan_documents(access: PlanAccess = _VIEW_ACCESS,
                              db: AsyncSession = Depends(get_db_with_user)) -> list[PlanDocumentOut]:
    """Dok 05 §3.3: SK, revisi, dan adendum beserta jumlah tanda tangan yang berlaku."""
    return _rows(await SignatureService(db).list_plan_documents(access.plan.id), PlanDocumentOut)


@router.get("/documents/{document_id}/signatures", response_model=list[SignatureOut])
async def list_signatures(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db_with_user)) -> list[SignatureOut]:
    return _rows(await SignatureService(db).list_signatures(current_user, document_id), SignatureOut)


@router.get("/documents/{document_id}/pdf", response_class=Response)
async def document_pdf(document_id: UUID, current_user: CurrentUser = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db_with_user)) -> Response:
    """PDF bertanda tangan + QR verifikasi (dok 05 §3.9). Render berat → threadpool (CLAUDE.md)."""
    document, signatures = await SignatureService(db).document_with_qr(current_user, document_id)
    html = render_plan_document_html(document, signatures)
    pdf = await run_in_threadpool(html_to_pdf, html)
    filename = f"{document.number}-v{document.version}.pdf".replace("/", "-")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.post("/signatures/{signature_id}/revoke")
async def revoke_signature(signature_id: UUID, data: RevokeRequest,
                           current_user: CurrentUser = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db_with_user)) -> dict[str, str]:
    """P6-6: pencabutan beserta alasan (PM unit/OPS SK tersebut); tercatat di audit."""
    await SignatureService(db).revoke_signature(current_user, signature_id, data.reason)
    return {"message": "Tanda tangan dicabut."}


@router.get("/verify/{token:path}", response_model=VerifyOut)
async def verify_signature(token: str, request: Request, db: AsyncSession = Depends(get_db)) -> VerifyOut:
    """PUBLIK: hasil pemindaian QR — hanya data yang perlu dilihat pemverifikasi (db/04 verify_signature_qr)."""
    _rate_limit(request.client.host if request.client else "unknown")
    row = await SignatureService(db).verify(token)
    data = dict(row._mapping)
    data["state"] = str(data["state"])
    data["signer_role"] = str(data["signer_role"]) if data.get("signer_role") else None
    return VerifyOut(**data)


