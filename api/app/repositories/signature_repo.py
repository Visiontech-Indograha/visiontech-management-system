"""
app/repositories/signature_repo.py
Tanda tangan dokumen ber-QR (fase 6). Logika inti hidup di db/04: register_document_signature
(nomor seri atomik + token QR), verify_signature_qr (VALID/REVOKED/KEY_EXPIRED/DOCUMENT_CHANGED),
issue_qr_token (db/02). Token QR mentah tidak pernah disimpan — hanya hash-nya.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class SignatureRepo(BaseRepo):

    async def ensure_signing_key(self, org_id: UUID | str, kid: str, public_key: bytes, kms_ref: str,
                                 algorithm: str) -> str:
        """Satu baris signing_key per (organisasi, kunci publik); hanya bagian publik yang disimpan."""
        key_id: str = await self.scalar(
            """
            INSERT INTO vms.signing_key (organization_id, kid, purpose, algorithm, public_key, kms_key_ref)
            VALUES (:org, :kid, 'DOCUMENT_SIGNATURE', :alg, :pub, :ref)
            ON CONFLICT (kid) DO UPDATE SET kid = EXCLUDED.kid
            RETURNING CAST(id AS text)
            """,
            {"org": org_id, "kid": kid, "alg": algorithm, "pub": public_key, "ref": kms_ref})
        return key_id

    async def plan_document(self, document_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT d.id, d.work_plan_id, wp.organization_id, d.number, d.version, CAST(d.kind AS text) AS kind,
                   CAST(d.status AS text) AS status, d.snapshot, d.snapshot_sha256, d.issued_at,
                   COALESCE(d.snapshot -> 'plan' ->> 'title', wp.title) AS title
            FROM vms.plan_document d JOIN vms.work_plan wp ON wp.id = d.work_plan_id
            WHERE d.id = :id
            """,
            {"id": document_id})

    async def plan_documents(self, plan_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT CAST(d.id AS text) AS id, CAST(d.kind AS text) AS kind, d.version, d.number,
                   CAST(d.status AS text) AS status, d.reason, d.issued_at, d.accepted_at,
                   encode(d.snapshot_sha256, 'hex') AS sha256,
                   (SELECT count(*) FROM vms.document_signature s
                     WHERE s.signable_type = 'plan_document' AND s.signable_id = d.id
                       AND s.revoked_at IS NULL) AS signature_count
            FROM vms.plan_document d WHERE d.work_plan_id = :plan
            ORDER BY d.version, d.issued_at
            """,
            {"plan": plan_id}))

    async def latest_document_id(self, plan_id: UUID | str) -> str | None:
        document_id: str | None = await self.scalar(
            """
            SELECT CAST(id AS text) FROM vms.plan_document
             WHERE work_plan_id = :plan ORDER BY version DESC, issued_at DESC LIMIT 1
            """,
            {"plan": plan_id})
        return document_id

    async def register(self, org_id: UUID | str, document: Any, signer_employee_id: str, role: str,
                       key_id: str, signature: bytes, payload: dict[str, Any], issued_by: str) -> Any:
        return await self.fetchone(
            """
            SELECT * FROM vms.register_document_signature(
                CAST(:org AS uuid), 'plan_document', CAST(:doc AS uuid), :number, :title, :sha,
                CAST(:signer AS uuid), CAST(:role AS vms.signature_role), CAST(:key AS uuid), :signature,
                CAST(:payload AS jsonb), CAST(:issued_by AS uuid))
            """,
            {"org": org_id, "doc": document.id, "number": document.number, "title": document.title,
             "sha": document.snapshot_sha256, "signer": signer_employee_id, "role": role, "key": key_id,
             "signature": signature, "payload": json.dumps(payload), "issued_by": issued_by})

    async def final_report_document(self, plan_id: UUID | str) -> Any:
        """Laporan akhir yang disetujui sebagai dokumen bertanda tangan (R-19). None bila belum ada."""
        return await self.fetchone(
            """
            SELECT wp.id, wp.organization_id, wp.number, wp.title, CAST(fr.status AS text) AS status,
                   fr.snapshot, fr.snapshot_sha256
            FROM vms.final_report fr JOIN vms.work_plan wp ON wp.id = fr.work_plan_id
            WHERE fr.work_plan_id = :plan
            """,
            {"plan": plan_id})

    async def register_final_report(self, org_id: UUID | str, plan: Any, signer_employee_id: str, role: str,
                                    key_id: str, signature: bytes, payload: dict[str, Any], issued_by: str) -> Any:
        return await self.fetchone(
            """
            SELECT * FROM vms.register_document_signature(
                CAST(:org AS uuid), 'final_report', CAST(:plan AS uuid), :number, :title, :sha,
                CAST(:signer AS uuid), CAST(:role AS vms.signature_role), CAST(:key AS uuid), :signature,
                CAST(:payload AS jsonb), CAST(:issued_by AS uuid))
            """,
            {"org": org_id, "plan": plan.id, "number": f"{plan.number}-LA", "title": f"Laporan akhir: {plan.title}",
             "sha": plan.snapshot_sha256, "signer": signer_employee_id, "role": role, "key": key_id,
             "signature": signature, "payload": json.dumps(payload), "issued_by": issued_by})

    async def signatures_of(self, signable_type: str, signable_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT CAST(s.id AS text) AS id, s.serial_number, s.signer_name, s.signer_position, s.signer_unit,
                   CAST(s.signer_role AS text) AS signer_role, s.signed_at, s.signature_alg, k.kid,
                   encode(s.document_sha256, 'hex') AS document_sha256_hex, s.revoked_at, s.revoked_reason
            FROM vms.document_signature s JOIN vms.signing_key k ON k.id = s.signing_key_id
            WHERE s.signable_type = :type AND s.signable_id = :id
            ORDER BY s.signed_at, s.serial_number
            """,
            {"type": signable_type, "id": signable_id}))

    async def signatures_of_document(self, document_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT CAST(s.id AS text) AS id, s.serial_number, s.signer_name, s.signer_position, s.signer_unit,
                   CAST(s.signer_role AS text) AS signer_role, s.signed_at, s.signature_alg, k.kid,
                   encode(s.document_sha256, 'hex') AS document_sha256_hex, s.revoked_at, s.revoked_reason
            FROM vms.document_signature s JOIN vms.signing_key k ON k.id = s.signing_key_id
            WHERE s.signable_type = 'plan_document' AND s.signable_id = :doc
            ORDER BY s.signed_at, s.serial_number
            """,
            {"doc": document_id}))

    async def signature(self, signature_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT s.id, s.organization_id, s.signable_id, s.revoked_at,
                   COALESCE(d.work_plan_id, CASE WHEN s.signable_type = 'final_report' THEN s.signable_id END)
                       AS work_plan_id
            FROM vms.document_signature s LEFT JOIN vms.plan_document d ON d.id = s.plan_document_id
            WHERE s.id = :id
            """,
            {"id": signature_id})

    async def employee_of(self, user_id: UUID | str) -> str | None:
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return employee

    async def revoke(self, signature_id: UUID | str, reason: str, employee_id: str | None) -> None:
        await self.execute(
            """
            UPDATE vms.document_signature SET revoked_at = now(), revoked_reason = :reason, revoked_by = :emp
             WHERE id = :id AND revoked_at IS NULL
            """,
            {"id": signature_id, "reason": reason, "emp": employee_id})

    async def issue_verify_token(self, org_id: UUID | str, signature_id: UUID | str, issued_by: str) -> str:
        raw: str = await self.scalar(
            """
            SELECT raw_token FROM vms.issue_qr_token(
                CAST(:org AS uuid), 'DOCUMENT_VERIFY', 'document_signature', CAST(:sig AS uuid), CAST(:by AS uuid))
            """,
            {"org": org_id, "sig": signature_id, "by": issued_by})
        return raw

    async def verify(self, raw_token: str) -> Any:
        return await self.fetchone("SELECT * FROM vms.verify_signature_qr(:token)", {"token": raw_token})
