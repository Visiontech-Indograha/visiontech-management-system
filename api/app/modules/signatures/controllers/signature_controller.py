"""
app/modules/signatures/controllers/signature_controller.py

Controller orkestrasi use case tanda tangan dokumen SK dan verifikasi publik.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response

import app.api.v1.endpoints.signatures as legacy_signatures_endpoint
from app.api.deps import get_public_signature_service, get_signature_service
from app.core.errors import AppError
from app.core.security import CurrentUser
from app.modules.signatures.schemas.signature_schema import (
    PlanDocumentOut,
    RevokeRequest,
    SignatureOut,
    VerifyOut,
)
from app.modules.signatures.services.signature_service import SignatureService
from app.services.pdf_service import html_to_pdf, render_plan_document_html

_verify_hits: dict[str, deque[float]] = defaultdict(deque)


class SignatureController:
    """
    Controller use case tanda tangan SK, rendering PDF/HTML, dan pencabutan tanda tangan.
    Memerlukan sesi terautentikasi pengguna.
    """

    def __init__(
        self,
        signature_service: SignatureService = Depends(get_signature_service),
    ) -> None:
        self.signature_service = signature_service

    async def handle_list_plan_documents(self, plan_id: UUID) -> list[PlanDocumentOut]:
        """Mengambil daftar dokumen SK, revisi, dan adendum untuk work plan."""
        rows = await self.signature_service.list_plan_documents(plan_id)
        return [PlanDocumentOut(**r._mapping) for r in rows]

    async def handle_list_signatures(
        self, current_user: CurrentUser, document_id: UUID
    ) -> list[SignatureOut]:
        """Mengambil daftar tanda tangan yang tercatat untuk sebuah dokumen."""
        rows = await self.signature_service.list_signatures(current_user, document_id)
        return [SignatureOut(**r._mapping) for r in rows]

    async def handle_document_pdf(
        self, current_user: CurrentUser, document_id: UUID
    ) -> Response:
        """Menghasilkan file PDF dokumen bertanda tangan dengan QR verifikasi."""
        document, signatures = await self.signature_service.document_with_qr(current_user, document_id)
        html = render_plan_document_html(document, signatures)
        pdf_func = getattr(legacy_signatures_endpoint, "html_to_pdf", html_to_pdf)
        pdf = await run_in_threadpool(pdf_func, html)
        filename = f"{document.number}-v{document.version}.pdf".replace("/", "-")
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    async def handle_document_html(
        self, current_user: CurrentUser, document_id: UUID
    ) -> HTMLResponse:
        """Menghasilkan representasi HTML dokumen bertanda tangan untuk penampil aplikasi."""
        document, signatures = await self.signature_service.document_with_qr(current_user, document_id)
        return HTMLResponse(render_plan_document_html(document, signatures))

    async def handle_revoke_signature(
        self, current_user: CurrentUser, signature_id: UUID, data: RevokeRequest
    ) -> dict[str, str]:
        """Mencabut tanda tangan digital yang telah dibubuhkan."""
        await self.signature_service.revoke_signature(current_user, signature_id, data.reason)
        return {"message": "Tanda tangan dicabut."}


class PublicSignatureController:
    """
    Controller use case verifikasi tanda tangan publik (tanpa autentikasi pengguna).
    """

    def __init__(
        self,
        public_signature_service: SignatureService = Depends(get_public_signature_service),
    ) -> None:
        self.public_signature_service = public_signature_service

    async def handle_verify(self, token: str, client_ip: str) -> VerifyOut:
        """Verifikasi keabsahan tanda tangan secara publik dari hasil pindai QR."""
        limit = getattr(legacy_signatures_endpoint, "VERIFY_LIMIT", 30)
        window = getattr(legacy_signatures_endpoint, "VERIFY_WINDOW", 60.0)
        hits_dict = getattr(legacy_signatures_endpoint, "_verify_hits", _verify_hits)

        now, hits = time.monotonic(), hits_dict[client_ip]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            raise AppError("TOO_MANY_REQUESTS", "Terlalu sering memeriksa. Coba lagi sebentar lagi.", status=429)
        hits.append(now)

        row = await self.public_signature_service.verify(token)
        data: dict[str, Any] = dict(row._mapping)
        data["state"] = str(data["state"])
        data["signer_role"] = str(data["signer_role"]) if data.get("signer_role") else None
        return VerifyOut(**data)
