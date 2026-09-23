"""
app/services/document_service.py
Aturan bisnis snapshot dokumen: kanonisasi, hashing, penomoran seri.
Dipakai oleh plan_service saat menerbitkan SK dan adendum.
"""
from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.plan_repo import PlanRepo


def canonical_json(data: dict) -> str:
    """
    Serialisasi JSON deterministik (RFC 8785):
    - Key diurutkan secara rekursif
    - Tanpa spasi
    - Nilai None → null
    - Tipe datetime/UUID → string via default=str
    Catatan: untuk produksi gunakan library `canonicaljson` untuk kepatuhan penuh RFC 8785.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def sha256_bytes(data: str) -> bytes:
    return hashlib.sha256(data.encode("utf-8")).digest()


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.plan_repo = PlanRepo(db)
        self.db = db

    async def build_plan_snapshot(self, plan_id: UUID) -> tuple[str, bytes]:
        """
        Ambil snapshot plan dari DB, kanonisasi, hash.
        Kembalikan (json_string, sha256_bytes).
        """
        raw = await self.plan_repo.get_snapshot(plan_id)
        if not raw:
            raise ValueError(f"Plan {plan_id} tidak ditemukan untuk snapshot.")
        data = dict(raw._mapping)
        snapshot_json = canonical_json(data)
        snapshot_sha = sha256_bytes(snapshot_json)
        return snapshot_json, snapshot_sha

    async def next_serial_number(
        self,
        org_id: UUID,
        prefix: str = "VTI",
    ) -> str:
        """
        Buat nomor seri dokumen berikutnya via DB function vms.next_signature_serial.
        Format hasil: VTI/2026/000042
        """
        from sqlalchemy import text
        result = await self.db.execute(
            text("SELECT vms.next_signature_serial(:org, :prefix)"),
            {"org": org_id, "prefix": prefix},
        )
        return result.scalar()

    async def register_document_snapshot(
        self,
        plan_id: UUID,
        org_id: UUID,
        issued_by_employee_id: UUID,
        kind: str = "SK",
        version: int = 1,
    ) -> dict:
        """
        Proses lengkap penerbitan dokumen:
        1. Ambil + kanonisasi snapshot
        2. Generate nomor seri
        3. Insert ke plan_document
        Kembalikan { document_id, number, snapshot_sha256_hex }
        """
        snapshot_json, snapshot_sha = await self.build_plan_snapshot(plan_id)
        number = await self.next_serial_number(org_id)
        doc = await self.plan_repo.create_document_snapshot(
            plan_id=plan_id,
            kind=kind,
            version=version,
            number=number,
            snapshot_json=snapshot_json,
            snapshot_sha=snapshot_sha,
            issued_by=issued_by_employee_id,
        )
        return {
            "document_id": str(doc.id),
            "number": number,
            "snapshot_sha256_hex": snapshot_sha.hex(),
        }
