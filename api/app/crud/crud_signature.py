"""
app/crud/crud_signature.py
Tanda tangan dokumen ber-QR (fase 6). Logika inti hidup di db/04: register_document_signature
(nomor seri atomik + token QR), verify_signature_qr (VALID/REVOKED/KEY_EXPIRED/DOCUMENT_CHANGED),
issue_qr_token (db/02). Token QR mentah tidak pernah disimpan — hanya hash-nya.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDSignature(CRUDBase):
    """
    CRUD untuk mengelola tanda tangan digital dokumen (dokumen rencana kerja dan laporan akhir).
    Termasuk pendaftaran kunci publik, penerbitan tanda tangan ber-QR, dan verifikasi.
    """

    async def ensure_signing_key(self, org_id: UUID | str, kid: str, public_key: bytes, kms_ref: str,
                                 algorithm: str) -> str:
        """
        Menyimpan atau memperbarui kunci publik yang digunakan untuk memverifikasi tanda tangan.
        Hanya bagian publik yang disimpan, tidak pernah kunci privatnya.
        
        Args:
            org_id (UUID | str): ID organisasi.
            kid (str): Key ID dari kunci.
            public_key (bytes): Byte kunci publik.
            kms_ref (str): Referensi KMS (Key Management Service).
            algorithm (str): Algoritma kriptografi (misal: RS256, ES256).
            
        Returns:
            str: ID kunci publik (signing_key_id).
        """
        # Melakukan upsert: menyisipkan kunci baru atau memperbarui kunci dengan kid yang sama
        # Kunci ini selalu di-set purpusenya sebagai 'DOCUMENT_SIGNATURE'.
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
        """
        Mengambil informasi dokumen rencana kerja (SK).
        
        Args:
            document_id (UUID | str): ID dokumen.
            
        Returns:
            Any: Record dokumen SK beserta status dan snapshot-nya.
        """
        # Melakukan INNER JOIN dengan work_plan untuk mendapatkan informasi terkait organisasi
        # dan menggunakan COALESCE untuk mengambil judul dari snapshot atau work_plan asli.
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
        """
        Mendaftar semua versi dokumen dari sebuah SK (Rencana Kerja).
        
        Args:
            plan_id (UUID | str): ID rencana kerja.
            
        Returns:
            list[Any]: Daftar dokumen beserta jumlah tanda tangan aktif.
        """
        # Menggunakan subquery skalar untuk menghitung tanda tangan aktif (yang belum di-revoke).
        # Mengubah hash SHA-256 dari bytea ke format string hex untuk kemudahan pembacaan.
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
        """
        Mendapatkan ID dokumen SK revisi terakhir/terbaru.
        
        Args:
            plan_id (UUID | str): ID rencana kerja.
            
        Returns:
            str | None: ID dokumen terbaru atau None.
        """
        # Mengurutkan berdasarkan versi dan tanggal terbit secara menurun dan mengambil 1 record (LIMIT 1).
        document_id: str | None = await self.scalar(
            """
            SELECT CAST(id AS text) FROM vms.plan_document
             WHERE work_plan_id = :plan ORDER BY version DESC, issued_at DESC LIMIT 1
            """,
            {"plan": plan_id})
        return document_id

    async def register(self, org_id: UUID | str, document: Any, signer_employee_id: str, role: str,
                       key_id: str, signature: bytes, payload: dict[str, Any], issued_by: str) -> Any:
        """
        Mendaftarkan tanda tangan untuk dokumen SK dengan memanggil fungsi basis data internal.
        
        Args:
            org_id (UUID | str): ID organisasi.
            document (Any): Objek/record dokumen SK.
            signer_employee_id (str): ID karyawan penandatangan.
            role (str): Peran (misal 'LEADER', 'PM').
            key_id (str): ID kunci penandatangan (signing key).
            signature (bytes): Data tanda tangan (kriptografik).
            payload (dict[str, Any]): Payload detail metadata.
            issued_by (str): ID pengguna yang menerbitkan tanda tangan.
            
        Returns:
            Any: Record hasil (signature_id, serial_number, qr_token_id, qr_raw_token).
        """
        # Memanggil stored procedure (fungsi basis data) `register_document_signature` 
        # untuk memastikan proses pencatatan tanda tangan + token QR terjadi dalam transaksi yang sama.
        return await self.fetchone(
            """
            SELECT signature_id, serial_number, qr_token_id, qr_raw_token FROM vms.register_document_signature(
                CAST(:org AS uuid), 'plan_document', CAST(:doc AS uuid), :number, :title, :sha,
                CAST(:signer AS uuid), CAST(:role AS vms.signature_role), CAST(:key AS uuid), :signature,
                CAST(:payload AS jsonb), CAST(:issued_by AS uuid))
            """,
            {"org": org_id, "doc": document.id, "number": document.number, "title": document.title,
             "sha": document.snapshot_sha256, "signer": signer_employee_id, "role": role, "key": key_id,
             "signature": signature, "payload": json.dumps(payload), "issued_by": issued_by})

    async def final_report_document(self, plan_id: UUID | str) -> Any:
        """
        Laporan akhir yang disetujui sebagai dokumen bertanda tangan (R-19).
        
        Args:
            plan_id (UUID | str): ID rencana kerja (SK).
            
        Returns:
            Any: Record laporan akhir, atau None bila belum ada.
        """
        # Melakukan INNER JOIN dengan work_plan untuk memuat judul dan nomor SK asli.
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
        """
        Mendaftarkan tanda tangan untuk Laporan Akhir (Final Report).
        
        Args:
            org_id (UUID | str): ID organisasi.
            plan (Any): Record rencana kerja (work_plan).
            signer_employee_id (str): ID karyawan penandatangan.
            role (str): Peran (misal 'LEADER', 'PM').
            key_id (str): ID kunci penandatangan (signing key).
            signature (bytes): Data tanda tangan (kriptografik).
            payload (dict[str, Any]): Payload detail metadata.
            issued_by (str): ID pengguna yang menerbitkan tanda tangan.
            
        Returns:
            Any: Record (signature_id, serial_number, qr_token_id, qr_raw_token).
        """
        # Seperti pada `register`, memanggil fungsi `register_document_signature`
        # namun disesuaikan untuk tipe dokumen 'final_report' dengan imbuhan '-LA' pada nomor.
        return await self.fetchone(
            """
            SELECT signature_id, serial_number, qr_token_id, qr_raw_token FROM vms.register_document_signature(
                CAST(:org AS uuid), 'final_report', CAST(:plan AS uuid), :number, :title, :sha,
                CAST(:signer AS uuid), CAST(:role AS vms.signature_role), CAST(:key AS uuid), :signature,
                CAST(:payload AS jsonb), CAST(:issued_by AS uuid))
            """,
            {"org": org_id, "plan": plan.id, "number": f"{plan.number}-LA", "title": f"Laporan akhir: {plan.title}",
             "sha": plan.snapshot_sha256, "signer": signer_employee_id, "role": role, "key": key_id,
             "signature": signature, "payload": json.dumps(payload), "issued_by": issued_by})

    async def signatures_of(self, signable_type: str, signable_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar riwayat tanda tangan dari sebuah dokumen generik.
        
        Args:
            signable_type (str): Tipe dokumen ('plan_document' atau 'final_report').
            signable_id (UUID | str): ID dokumen tersebut.
            
        Returns:
            list[Any]: Daftar record tanda tangan yang terkait.
        """
        # Melakukan INNER JOIN pada signing_key untuk mengaitkan penandatangan dengan Key ID.
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
        """
        Mengambil daftar riwayat tanda tangan khusus untuk dokumen rencana kerja (SK).
        
        Args:
            document_id (UUID | str): ID dokumen SK.
            
        Returns:
            list[Any]: Daftar record tanda tangan terkait dokumen SK.
        """
        # Sama dengan signatures_of namun dikhususkan hanya untuk 'plan_document'.
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
        """
        Mengambil info dari satu entri tanda tangan.
        
        Args:
            signature_id (UUID | str): ID tanda tangan.
            
        Returns:
            Any: Record metadata tanda tangan.
        """
        # Menggunakan COALESCE agar dapat memetakan ID SK (work_plan_id) secara dinamis
        # baik jika tanda tangan itu milik dokumen SK atau langsung dari final_report.
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
        """
        Mengambil ID karyawan dari sebuah ID pengguna aplikasi.
        
        Args:
            user_id (UUID | str): ID pengguna.
            
        Returns:
            str | None: ID karyawan, atau None.
        """
        # Simple scalar select untuk app_user
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return employee

    async def revoke(self, signature_id: UUID | str, reason: str, employee_id: str | None) -> None:
        """
        Mencabut sebuah tanda tangan yang sudah direkam.
        
        Args:
            signature_id (UUID | str): ID tanda tangan.
            reason (str): Alasan pencabutan.
            employee_id (str | None): Karyawan yang mencabut.
        """
        # Update dengan set kolom revoked_at menjadi now() tanpa menghapus barisnya (soft-revoke).
        await self.execute(
            """
            UPDATE vms.document_signature SET revoked_at = now(), revoked_reason = :reason, revoked_by = :emp
             WHERE id = :id AND revoked_at IS NULL
            """,
            {"id": signature_id, "reason": reason, "emp": employee_id})

    async def issue_verify_token(self, org_id: UUID | str, signature_id: UUID | str, issued_by: str) -> str:
        """
        Menerbitkan token QR baru (berupa JWT internal) untuk memverifikasi tanda tangan.
        
        Args:
            org_id (UUID | str): ID organisasi.
            signature_id (UUID | str): ID tanda tangan.
            issued_by (str): Pengguna yang mencetak/menerbitkan kode QR.
            
        Returns:
            str: Token QR string (raw_token).
        """
        # Memanggil fungsi tersimpan `issue_qr_token` yang akan men-generate random identifier
        # lalu memetakan token QR sementara khusus untuk dokumen verifikasi (DOCUMENT_VERIFY).
        raw: str = await self.scalar(
            """
            SELECT raw_token FROM vms.issue_qr_token(
                CAST(:org AS uuid), 'DOCUMENT_VERIFY', 'document_signature', CAST(:sig AS uuid), CAST(:by AS uuid))
            """,
            {"org": org_id, "sig": signature_id, "by": issued_by})
        return raw

    async def verify(self, raw_token: str) -> Any:
        """
        Memverifikasi tanda tangan menggunakan raw token (hasil scan QR).
        
        Args:
            raw_token (str): String token hasil scan.
            
        Returns:
            Any: Record hasil verifikasi (status, informasi penandatangan, hash dokumen).
        """
        # Memanggil fungsi `verify_signature_qr` yang mencakup semua validasi kompleks:
        # Pengecekan token kadaluarsa, revokasi, status key, maupun integritas dokumen.
        return await self.fetchone("SELECT state, serial_number, signer_name, signer_position, signer_unit, signer_role, document_number, document_title, signed_at, key_id, algorithm, document_sha256_hex, note FROM vms.verify_signature_qr(:token)", {"token": raw_token})
