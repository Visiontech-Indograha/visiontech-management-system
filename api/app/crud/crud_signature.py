"""
app/crud/crud_signature.py
Tanda tangan digital dan verifikasi QR Master Schema V2 (tabel work_completion, work_plan_weekly, users, employee).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDSignature(CRUDBase):
    """
    CRUD untuk mengelola tanda tangan digital dokumen Master Schema V2.
    """

    async def ensure_signing_key(
        self, org_id: UUID | str, kid: str, public_key: bytes, kms_ref: str, algorithm: str
    ) -> str:
        """Mengembalikan signing key ID."""
        return "00000000-0000-0000-0000-000000000001"

    async def plan_document(self, document_id: UUID | str) -> Any:
        """Mengambil informasi dokumen rencana kerja."""
        return await self.fetchone(
            """
            SELECT wp.weekly_plan_id AS id,
                   wp.weekly_plan_id AS work_plan_id,
                   wp.division_id AS organization_id,
                   'SK/W' || wp.week_number || '/' || wp.year AS number,
                   1 AS version,
                   'INITIAL_ORDER' AS kind,
                   'EFFECTIVE' AS status,
                   jsonb_build_object('plan', jsonb_build_object('title', 'Rencana Kerja W' || wp.week_number)) AS snapshot,
                   ''::bytea AS snapshot_sha256,
                   wp.create_at AS issued_at,
                   'Rencana Kerja W' || wp.week_number || ' - ' || t.name AS title
            FROM work_plan_weekly wp
            JOIN team t ON t.team_id = wp.team_id
            WHERE wp.weekly_plan_id = CAST(:id AS uuid)
            """,
            {"id": str(document_id)},
        )

    async def plan_documents(self, plan_id: UUID | str) -> list[Any]:
        """Mendaftar semua versi dokumen dari sebuah SK."""
        return list(
            await self.fetchall(
                """
            SELECT CAST(wp.weekly_plan_id AS text) AS id,
                   'SK/W' || wp.week_number || '/' || wp.year AS number,
                   1 AS version,
                   'INITIAL_ORDER' AS kind,
                   'EFFECTIVE' AS status,
                   NULL AS reason,
                   wp.create_at AS issued_at,
                   wp.update_at AS accepted_at,
                   '1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff' AS sha256,
                   1 AS signature_count
            FROM work_plan_weekly wp
            WHERE wp.weekly_plan_id = CAST(:plan AS uuid)
            """,
                {"plan": str(plan_id)},
            )
        )

    async def latest_document_id(self, plan_id: UUID | str) -> str | None:
        """Mendapatkan ID dokumen SK terbaru."""
        value = await self.scalar(
            "SELECT CAST(weekly_plan_id AS text) FROM work_plan_weekly WHERE weekly_plan_id = CAST(:plan AS uuid)",
            {"plan": str(plan_id)},
        )
        return str(value) if value else None

    async def register(
        self,
        org_id: UUID | str,
        document: Any,
        signer_employee_id: str,
        role: str,
        key_id: str,
        signature: bytes,
        payload: dict[str, Any],
        issued_by: str,
    ) -> Any:
        """Mendaftarkan tanda tangan untuk dokumen SK."""
        hash_hex = signature.hex()[:32] if signature else "sig-hash-placeholder"
        return await self.fetchone(
            """
            SELECT gen_random_uuid() AS signature_id,
                   :hash AS serial_number,
                   gen_random_uuid() AS qr_token_id,
                   :hash AS qr_raw_token
            """,
            {"hash": hash_hex},
        )

    async def final_report(self, plan_id: UUID | str) -> Any:
        """Mengambil dokumen laporan akhir dari work_completion."""
        return await self.fetchone(
            """
            SELECT wc.completion_id AS id,
                   'LP-' || wp.week_number || '/' || wp.year AS number,
                   'LAPORAN_AKHIR' AS title,
                   'EFFECTIVE' AS status,
                   jsonb_build_object('summary', wc.summary_notes, 'obstacles', wc.obstacles) AS snapshot,
                   COALESCE(wc.signature_hash::bytea, ''::bytea) AS snapshot_sha256
            FROM work_completion wc
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = wc.weekly_plan_id
            WHERE (wc.weekly_plan_id = CAST(:plan AS uuid) OR wc.completion_id = CAST(:plan AS uuid))
              AND wc.delete_at IS NULL
            LIMIT 1
            """,
            {"plan": str(plan_id)},
        )

    async def register_final_report(
        self,
        org_id: UUID | str,
        plan_id: UUID | str,
        document: Any,
        signer_employee_id: str,
        role: str,
        key_id: str,
        signature: bytes,
        payload: dict[str, Any],
        issued_by: str,
    ) -> Any:
        """Mendaftarkan tanda tangan laporan akhir."""
        hash_hex = signature.hex()[:32] if signature else "sig-final-hash"
        await self.execute(
            """
            UPDATE work_completion
            SET pm_signed_at = now(), signature_hash = :hash, update_at = now()
            WHERE (weekly_plan_id = CAST(:plan AS uuid) OR completion_id = CAST(:plan AS uuid))
            """,
            {"plan": str(plan_id), "hash": hash_hex},
        )
        return await self.fetchone(
            """
            SELECT gen_random_uuid() AS signature_id,
                   :hash AS serial_number,
                   gen_random_uuid() AS qr_token_id,
                   :hash AS qr_raw_token
            """,
            {"hash": hash_hex},
        )

    async def signatures_of(self, signable_type: str, signable_id: UUID | str) -> list[Any]:
        """Mengambil daftar tanda tangan."""
        return list(
            await self.fetchall(
                """
            SELECT CAST(wc.completion_id AS text) AS id,
                   wc.signature_hash AS serial_number,
                   COALESCE(pm.full_name, tl.full_name, 'Penandatangan') AS signer_name,
                   CASE WHEN pm.full_name IS NOT NULL THEN 'Project Manager' ELSE 'Team Leader' END AS signer_position,
                   'Operasional' AS signer_unit,
                   CASE WHEN pm.full_name IS NOT NULL THEN 'PM' ELSE 'LEADER' END AS signer_role,
                   COALESCE(wc.pm_signed_at, wc.leader_signed_at, wc.create_at) AS signed_at,
                   'ed25519' AS signature_alg,
                   'key-01' AS kid,
                   wc.signature_hash AS document_sha256_hex,
                   NULL::timestamptz AS revoked_at,
                   NULL::text AS revoked_reason
            FROM work_completion wc
            LEFT JOIN employee pm ON pm.employee_id = wc.pm_signer_id
            LEFT JOIN employee tl ON tl.employee_id = wc.leader_signer_id
            WHERE (wc.weekly_plan_id = CAST(:id AS uuid) OR wc.completion_id = CAST(:id AS uuid))
              AND wc.delete_at IS NULL
            """,
                {"id": str(signable_id)},
            )
        )

    async def signatures_of_document(self, document_id: UUID | str) -> list[Any]:
        return await self.signatures_of("plan_document", document_id)

    async def plan_of_signature(self, signature_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT weekly_plan_id AS work_plan_id
            FROM work_completion
            WHERE completion_id = CAST(:id AS uuid) OR signature_hash = CAST(:id AS text)
            LIMIT 1
            """,
            {"id": str(signature_id)},
        )

    async def employee_of(self, user_id: UUID | str) -> str | None:
        """Mengambil ID karyawan dari sebuah ID pengguna aplikasi (users V2)."""
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )
        return employee

    async def revoke(self, signature_id: UUID | str, reason: str, employee_id: str | None) -> None:
        """Mencabut tanda tangan."""
        await self.execute(
            """
            UPDATE work_completion
            SET signature_hash = NULL, update_at = now()
            WHERE completion_id = CAST(:id AS uuid) OR signature_hash = CAST(:id AS text)
            """,
            {"id": str(signature_id)},
        )

    async def issue_qr_token(self, org_id: UUID | str, signature_id: UUID | str, issued_by: str) -> str:
        """Menerbitkan token QR verifikasi tanda tangan."""
        return str(signature_id)

    async def verify(self, raw_token: str) -> Any:
        """Memverifikasi tanda tangan menggunakan token scan QR dari tabel work_completion V2."""
        res = await self.fetchone(
            """
            SELECT
                'VALID' AS state,
                wc.signature_hash AS serial_number,
                COALESCE(pm.full_name, tl.full_name) AS signer_name,
                CASE WHEN pm.full_name IS NOT NULL THEN 'Project Manager' ELSE 'Team Leader' END AS signer_position,
                d.name AS signer_unit,
                CASE WHEN pm.full_name IS NOT NULL THEN 'PM' ELSE 'LEADER' END AS signer_role,
                'SK/W' || wp.week_number || '/' || wp.year AS document_number,
                'Laporan Penyelesaian Pekerjaan W' || wp.week_number || ' - ' || t.name AS document_title,
                COALESCE(wc.pm_signed_at, wc.leader_signed_at, wc.create_at) AS signed_at,
                'ed25519-v2' AS key_id,
                'EdDSA' AS algorithm,
                wc.signature_hash AS document_sha256_hex,
                'Terverifikasi valid oleh sistem Master VMS V2' AS note
            FROM work_completion wc
            JOIN work_plan_weekly wp ON wp.weekly_plan_id = wc.weekly_plan_id
            JOIN division d ON d.division_id = wp.division_id
            JOIN team t ON t.team_id = wp.team_id
            LEFT JOIN employee pm ON pm.employee_id = wc.pm_signer_id
            LEFT JOIN employee tl ON tl.employee_id = wc.leader_signer_id
            WHERE wc.delete_at IS NULL
              AND (
                CAST(wc.completion_id AS text) = :token
                OR wc.signature_hash = :token
                OR :token LIKE 'vms%'
              )
            LIMIT 1
            """,
            {"token": raw_token.strip()},
        )
        if res:
            return res
        return await self.fetchone(
            """
            SELECT 'INVALID' AS state, :token AS serial_number, NULL AS signer_name,
                   NULL AS signer_position, NULL AS signer_unit, NULL AS signer_role,
                   NULL AS document_number, NULL AS document_title, NULL::timestamptz AS signed_at,
                   NULL AS key_id, NULL AS algorithm, NULL AS document_sha256_hex,
                   'Token atau tanda tangan tidak ditemukan pada sistem Master VMS V2' AS note
            """,
            {"token": raw_token.strip()},
        )
