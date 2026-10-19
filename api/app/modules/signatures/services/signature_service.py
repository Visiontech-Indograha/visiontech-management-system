"""
app/services/signature_service.py
Tanda tangan dokumen SK ber-QR (fase 6; keputusan pemilik 2026-09-26: otomatis — PM sebagai ISSUER saat
terbit, ketua sebagai ACCEPTOR saat menerima). Payload JSON kanonik RFC 8785 ditandatangani lewat
`DocumentSigner` (lokal dulu, KMS nanti). Verifikasi publik memakai `verify_signature_qr` (db/04).
"""

from __future__ import annotations

import base64
import io
from typing import Any
from urllib.parse import quote
from uuid import UUID

import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.signing import canonical, get_document_signer
from app.modules.signatures.repositories.signature_repository import CRUDSignature
from app.services.access_service import PlanNeed, check_plan_access

ISSUER = "ISSUER"
ACCEPTOR = "ACCEPTOR"
APPROVER = "APPROVER"


def verify_url(raw_token: str) -> str:
    """Membangun URL verifikasi publik yang lengkap berdasarkan raw token."""
    return f"{settings.PUBLIC_VERIFY_URL.rstrip('/')}/{quote(raw_token, safe='')}"


def qr_png_data_uri(text: str) -> str:
    """Menghasilkan Data URI gambar QR Code format PNG untuk teks/URL yang diberikan."""
    buffer = io.BytesIO()
    qrcode.make(text, box_size=6, border=2).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class SignatureService:
    """
    Layanan untuk mengelola tanda tangan elektronik pada dokumen SK dan laporan akhir.
    Menggunakan mekanisme payload JSON kanonik dan public key cryptography untuk menghasilkan tanda tangan.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi SignatureService.

        Args:
            db (AsyncSession): Sesi database asinkron.
        """
        self.db = db
        self.repo = CRUDSignature(db)

    async def _signing_key(self, org_id: Any, signer: Any) -> str:
        """Baris signing_key MILIK organisasi ini. `kid` memakai id organisasi lengkap — dulu 8 karakter
        awal (cap waktu UUIDv7), sehingga organisasi yang dibuat berdekatan berbagi kunci (temuan R-19)."""
        return await self.repo.ensure_signing_key(
            org_id, f"doc-{org_id}-{signer.fingerprint}", signer.public_key, signer.kms_ref, signer.algorithm
        )

    async def sign_plan_document(
        self, document_id: UUID | str, signer_employee_id: str, role: str, issued_by_user: str
    ) -> Any:
        """
        Menandatangani dokumen SK secara elektronik (menghasilkan hash dari payload kanonik).

        Args:
            document_id (UUID | str): ID dari dokumen yang akan ditandatangani.
            signer_employee_id (str): ID Karyawan yang menandatangani.
            role (str): Peran penandatangan (contoh: ISSUER, ACCEPTOR).
            issued_by_user (str): ID pengguna yang melakukan proses ini.

        Returns:
            Any: Data tanda tangan yang tersimpan.
        """
        document = await self.repo.plan_document(document_id)
        if document is None:
            raise NotFoundError("Dokumen")
        signer = get_document_signer()
        key_id = await self._signing_key(document.organization_id, signer)
        payload = {
            "type": "plan_document",
            "document_id": str(document.id),
            "document_number": document.number,
            "document_version": document.version,
            "document_sha256": bytes(document.snapshot_sha256).hex(),
            "signer_employee_id": str(signer_employee_id),
            "signer_role": role,
            "organization_id": str(document.organization_id),
        }
        # Menghasilkan signature kriptografi dari payload kanonik JSON
        signature = signer.sign(canonical(payload))
        return await self.repo.register(
            document.organization_id, document, signer_employee_id, role, key_id, signature, payload, issued_by_user
        )

    async def sign_latest_plan_document(
        self, plan_id: UUID | str, signer_employee_id: str, role: str, issued_by_user: str
    ) -> Any:
        """
        Menemukan dokumen terbaru dari suatu SK dan menandatanganinya.

        Args:
            plan_id (UUID | str): ID SK.
            signer_employee_id (str): ID Karyawan penandatangan.
            role (str): Peran (ISSUER/ACCEPTOR).
            issued_by_user (str): ID pengguna.

        Returns:
            Any: Data tanda tangan yang tersimpan.
        """
        document_id = await self.repo.latest_document_id(plan_id)
        if document_id is None:
            raise NotFoundError("Dokumen")
        return await self.sign_plan_document(document_id, signer_employee_id, role, issued_by_user)

    async def _document_for(self, user: CurrentUser, document_id: UUID) -> Any:
        """
        Mengambil data dokumen berdasarkan ID dengan memverifikasi akses VIEW terhadap SK terkait.

        Args:
            user (CurrentUser): Pengguna.
            document_id (UUID): ID dokumen.

        Returns:
            Any: Data dokumen.
        """
        document = await self.repo.plan_document(document_id)
        if document is None or str(document.organization_id) != str(user.organization_id):
            raise NotFoundError("Dokumen")
        await check_plan_access(self.db, document.work_plan_id, user, PlanNeed.VIEW)  # tak terlihat → 404
        return document

    async def sign_final_report(
        self, plan_id: UUID | str, signer_employee_id: str, role: str, issued_by_user: str
    ) -> Any:
        """Laporan akhir yang disetujui (R-19, P6-4): payload kanonik atas snapshot SHA-256-nya."""
        plan = await self.repo.final_report_document(plan_id)
        if plan is None or plan.snapshot_sha256 is None:
            raise NotFoundError("Laporan akhir")
        signer = get_document_signer()
        key_id = await self._signing_key(plan.organization_id, signer)
        payload = {
            "type": "final_report",
            "document_id": str(plan.id),
            "document_number": f"{plan.number}-LA",
            "document_sha256": bytes(plan.snapshot_sha256).hex(),
            "signer_employee_id": str(signer_employee_id),
            "signer_role": role,
            "organization_id": str(plan.organization_id),
        }
        return await self.repo.register_final_report(
            plan.organization_id,
            plan,
            signer_employee_id,
            role,
            key_id,
            signer.sign(canonical(payload)),
            payload,
            issued_by_user,
        )

    async def final_report_signatures(self, plan_id: UUID) -> list[Any]:
        """Tanda tangan laporan akhir — akses VIEW SK diperiksa penjaga rute."""
        return await self.repo.signatures_of("final_report", plan_id)

    async def final_report_with_qr(self, user: CurrentUser, plan_id: UUID) -> tuple[Any, list[dict[str, Any]]]:
        """Laporan akhir yang disetujui + tanda tangan ber-QR baru, untuk PDF."""
        plan = await self.repo.final_report_document(plan_id)
        if plan is None or plan.status != "APPROVED" or plan.snapshot is None:
            raise AppError("INVALID_STATE", "PDF laporan akhir tersedia setelah penyelesaian disetujui.", status=409)
        signed = []
        for sig in await self.repo.signatures_of("final_report", plan_id):
            row = dict(sig._mapping)
            if sig.revoked_at is None:
                url = verify_url(await self.repo.issue_verify_token(plan.organization_id, sig.id, user.user_id))
                row.update(verify_url=url, qr=qr_png_data_uri(url))
            signed.append(row)
        return plan, signed

    async def list_plan_documents(self, plan_id: UUID) -> list[Any]:
        """
        Daftar dokumen SK terkait.

        Args:
            plan_id (UUID): ID SK.

        Returns:
            list[Any]: Daftar dokumen.
        """
        return await self.repo.plan_documents(plan_id)

    async def list_signatures(self, user: CurrentUser, document_id: UUID) -> list[Any]:
        """
        Daftar tanda tangan yang tersemat pada suatu dokumen.

        Args:
            user (CurrentUser): Pengguna pembuat request.
            document_id (UUID): ID Dokumen.

        Returns:
            list[Any]: Daftar tanda tangan.
        """
        await self._document_for(user, document_id)
        return await self.repo.signatures_of_document(document_id)

    async def document_with_qr(self, user: CurrentUser, document_id: UUID) -> tuple[Any, list[dict[str, Any]]]:
        """Dokumen + tanda tangan beserta QR baru (token mentah tidak pernah disimpan, jadi diterbitkan ulang)."""
        document = await self._document_for(user, document_id)
        signed = []
        for sig in await self.repo.signatures_of_document(document_id):
            row = dict(sig._mapping)
            if sig.revoked_at is None:
                url = verify_url(await self.repo.issue_verify_token(document.organization_id, sig.id, user.user_id))
                row.update(verify_url=url, qr=qr_png_data_uri(url))
            signed.append(row)
        return document, signed

    async def revoke_signature(self, user: CurrentUser, signature_id: UUID, reason: str) -> None:
        """Pencabutan (P6-6): PM unit/OPS SK tersebut, alasan wajib, tercatat (audit trigger)."""
        sig = await self.repo.signature(signature_id)
        if sig is None or str(sig.organization_id) != str(user.organization_id):
            raise NotFoundError("Tanda tangan")
        await check_plan_access(self.db, sig.work_plan_id, user, PlanNeed.PM_UNIT)
        if not reason.strip():
            raise ValidationError("Alasan pencabutan wajib diisi.")
        if sig.revoked_at is not None:
            raise AppError("INVALID_STATE", "Tanda tangan sudah dicabut.", status=409)
        await self.repo.revoke(signature_id, reason.strip(), await self.repo.employee_of(user.user_id))

    async def verify(self, raw_token: str) -> Any:
        """
        Memverifikasi tanda tangan berdasarkan token unik dari QR Code.

        Args:
            raw_token (str): Token yang didapat dari scan QR code.

        Returns:
            Any: Data tanda tangan jika valid, atau None/raise Error.
        """
        return await self.repo.verify(raw_token)
