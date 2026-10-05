"""
app/crud/crud_face.py
Pengenalan wajah untuk absensi HP: persetujuan biometrik, pendaftaran, gambar wajah sementara (probe), dan
pencocokan. Seluruh SQL wajah ada di sini. Embedding dikirim sebagai literal pgvector (`[a,b,...]`) dan
TIDAK PERNAH dicatat ke log.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from .base import CRUDBase


def vector_literal(values: Sequence[float]) -> str:
    """Literal pgvector dari daftar angka."""
    return "[" + ",".join(f"{float(v):.6f}" for v in values) + "]"


def parse_vector(text: str | None) -> list[float] | None:
    """Parse keluaran pgvector (`[0.1,0.2,...]`) menjadi daftar angka."""
    if not text:
        return None
    return [float(v) for v in json.loads(text)]


class CRUDFace(CRUDBase):
    """CRUD wajah. RLS membatasi pembacaan pada pemilik data, HR, dan ADMIN (docs/08 §6)."""

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """Karyawan milik akun (employee_id, attendance_mode, unit_id); None bila akun belum tertaut."""
        return await self.fetchone(
            """
            SELECT e.id AS employee_id, e.attendance_mode, e.unit_id
            FROM vms.app_user u JOIN vms.employee e ON e.id = u.employee_id
            WHERE u.id = :uid AND e.is_active AND e.deleted_at IS NULL
            """,
            {"uid": user_id},
        )

    async def org_settings(self, org_id: UUID | str) -> Any:
        """Ambang & kebijakan wajah organisasi (dapat dikalibrasi tanpa rilis ulang)."""
        return await self.fetchone(
            """
            SELECT face_match_threshold, face_liveness_required, face_probe_retention_days
            FROM vms.organization WHERE id = :org
            """,
            {"org": org_id},
        )

    async def latest_consent(self, employee_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT state, policy_version, recorded_at FROM vms.biometric_consent
            WHERE employee_id = :emp ORDER BY recorded_at DESC LIMIT 1
            """,
            {"emp": employee_id},
        )

    async def record_consent(self, employee_id: UUID | str, state: str, purpose_text: str, policy_version: str,
                             user_id: UUID | str) -> None:
        """Mencatat persetujuan/penarikan. Menarik persetujuan menonaktifkan seluruh embedding lewat trigger DB."""
        await self.execute(
            """
            INSERT INTO vms.biometric_consent (employee_id, state, purpose_text, policy_version, recorded_by)
            VALUES (:emp, CAST(:state AS vms.consent_state), :purpose, :version, :uid)
            """,
            {"emp": employee_id, "state": state, "purpose": purpose_text, "version": policy_version, "uid": user_id},
        )

    async def active_enrollments(self, employee_id: UUID | str) -> Sequence[Any]:
        return await self.fetchall(
            """
            SELECT id, CAST(embedding AS text) AS embedding, model_name, model_version, captured_at
            FROM vms.face_enrollment WHERE employee_id = :emp AND is_active ORDER BY captured_at, id
            """,
            {"emp": employee_id},
        )

    async def deactivate_enrollments(self, employee_id: UUID | str, reason: str) -> None:
        await self.execute(
            """
            UPDATE vms.face_enrollment
               SET is_active = false, deactivated_at = now(), deactivate_reason = :reason
             WHERE employee_id = :emp AND is_active
            """,
            {"emp": employee_id, "reason": reason},
        )

    async def insert_enrollment(self, org_id: UUID | str, employee_id: UUID | str, embedding: Sequence[float],
                                model_name: str, model_version: str, quality: float | None,
                                user_id: UUID | str) -> None:
        # Trigger DB menolak bila persetujuan biometrik tidak berlaku (defense in depth).
        await self.execute(
            """
            INSERT INTO vms.face_enrollment (organization_id, employee_id, embedding, model_name, model_version,
                                             quality_score, enrolled_by)
            VALUES (:org, :emp, CAST(:emb AS vector), :model, :version, :quality, :uid)
            """,
            {"org": org_id, "emp": employee_id, "emb": vector_literal(embedding), "model": model_name,
             "version": model_version, "quality": quality, "uid": user_id},
        )

    async def best_other_similarity(self, org_id: UUID | str, employee_id: UUID | str,
                                    embedding: Sequence[float]) -> float | None:
        """Kemiripan tertinggi dengan karyawan LAIN (tanpa menyebut siapa) — menolak pendaftaran ganda."""
        value = await self.scalar(
            "SELECT vms.face_best_other_similarity(CAST(:org AS uuid), CAST(:emp AS uuid), CAST(:emb AS vector))",
            {"org": org_id, "emp": employee_id, "emb": vector_literal(embedding)},
        )
        return None if value is None else float(value)

    # ── Gambar wajah sementara (probe) ───────────────────────────────────────────────────────────
    async def insert_file_object(self, *, file_id: UUID | str, org_id: UUID | str, storage_key: str, name: str,
                                 mime: str, size: int, sha256: bytes, user_id: UUID | str) -> None:
        await self.execute(
            """
            INSERT INTO vms.file_object (id, organization_id, storage_key, file_name, mime_type, byte_size, sha256,
                                         uploaded_by)
            VALUES (:id, :org, :key, :name, :mime, :size, :sha, :uid)
            """,
            {"id": file_id, "org": org_id, "key": storage_key, "name": name, "mime": mime, "size": size,
             "sha": sha256, "uid": user_id},
        )

    async def insert_probe(self, *, probe_id: UUID | str, org_id: UUID | str, employee_id: UUID | str,
                           embedding: Sequence[float] | None, model_name: str | None, model_version: str | None,
                           quality: float | None, liveness: dict[str, Any], file_id: UUID | str,
                           sha256: bytes) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.face_probe (id, organization_id, employee_id, embedding, model_name, model_version,
                                        quality_score, liveness, file_id, sha256)
            VALUES (:id, :org, :emp, CAST(:emb AS vector), :model, :version, :quality,
                    CAST(:liveness AS jsonb), :file, :sha)
            RETURNING id, created_at
            """,
            {"id": probe_id, "org": org_id, "emp": employee_id,
             "emb": None if embedding is None else vector_literal(embedding), "model": model_name,
             "version": model_version, "quality": quality, "liveness": json.dumps(liveness), "file": file_id,
             "sha": sha256},
        )

    async def get_probe(self, probe_id: UUID | str) -> Any:
        """Probe (RLS: milik sendiri / HR / ADMIN). Dikunci agar tidak dipakai dua absen sekaligus."""
        return await self.fetchone(
            """
            SELECT id, organization_id, employee_id, CAST(embedding AS text) AS embedding, model_name, model_version,
                   quality_score, liveness, file_id, sha256, created_at, consumed_at
            FROM vms.face_probe WHERE id = :id FOR UPDATE
            """,
            {"id": probe_id},
        )

    async def consume_probe(self, probe_id: UUID | str, event: str, attendance_id: UUID | str) -> None:
        await self.execute(
            """
            UPDATE vms.face_probe SET consumed_at = now(), consumed_event = :ev, attendance_id = :att
            WHERE id = :id
            """,
            {"id": probe_id, "ev": event, "att": attendance_id},
        )

    async def verify(self, *, org_id: UUID | str, employee_id: UUID | str, embedding: Sequence[float],
                     liveness: float, probe_file_id: UUID | str | None, device: str | None, event: str) -> Any:
        """Pencocokan 1:1 di basis data (`verify_face_for_attendance`): hasil, kemiripan, ambang, catatan, id face_check."""
        return await self.fetchone(
            """
            SELECT result, similarity, threshold, matched_employee, note, check_id
            FROM vms.verify_face_for_attendance(CAST(:org AS uuid), CAST(:emp AS uuid), CAST(:emb AS vector),
                                                CAST(:live AS numeric), CAST(:file AS uuid), :device, :event)
            """,
            {"org": org_id, "emp": employee_id, "emb": vector_literal(embedding), "live": liveness,
             "file": probe_file_id, "device": device, "event": event},
        )

    async def link_check(self, check_id: UUID | str, attendance_id: UUID | str) -> None:
        """Mengaitkan catatan pencocokan dengan absensinya (face_check.attendance_id)."""
        await self.execute("UPDATE vms.face_check SET attendance_id = :att WHERE id = :id",
                           {"id": check_id, "att": attendance_id})

    # ── Pemeriksaan ulang & retensi (penjadwal, token ADMIN) ────────────────────────────────────────
    async def pending_probes(self, limit: int = 50) -> Sequence[Any]:
        """Probe yang dipakai absen saat face-service mati (embedding kosong): perlu dihitung & diperiksa ulang."""
        return await self.fetchall(
            """
            SELECT fp.id, fp.organization_id, fp.employee_id, fp.liveness, fp.consumed_event, fp.attendance_id,
                   fp.file_id, fo.storage_key
            FROM vms.face_probe fp JOIN vms.file_object fo ON fo.id = fp.file_id
            WHERE fp.embedding IS NULL AND fp.attendance_id IS NOT NULL
            ORDER BY fp.created_at LIMIT :n
            """,
            {"n": limit},
        )

    async def set_probe_embedding(self, probe_id: UUID | str, embedding: Sequence[float], model_name: str,
                                  model_version: str, quality: float | None) -> None:
        await self.execute(
            """
            UPDATE vms.face_probe SET embedding = CAST(:emb AS vector), model_name = :model,
                   model_version = :version, quality_score = :quality
            WHERE id = :id
            """,
            {"id": probe_id, "emb": vector_literal(embedding), "model": model_name, "version": model_version,
             "quality": quality},
        )

    async def expired_files(self) -> Sequence[Any]:
        """Kunci objek gambar wajah yang lewat masa simpan (dihapus dari MinIO sebelum purge)."""
        return await self.fetchall("SELECT file_id, storage_key FROM vms.expired_face_probe_files()")

    async def purge(self) -> int:
        return int(await self.scalar("SELECT vms.purge_face_probes()") or 0)
