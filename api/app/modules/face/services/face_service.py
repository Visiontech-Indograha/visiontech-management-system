"""
app/modules/face/services/face_service.py
Wajah V2 sederhana (Milestone 7, keputusan pemilik 2026-10-20; docs/35 §5).

- Pendaftaran: pekerja lapangan mengunggah 3–5 foto wajahnya sendiri → face-service menghitung embedding per foto →
  rata-rata (dinormalkan) disimpan di `employee.face_embedding`. Ditolak bila: bukan tepat satu wajah, kualitas rendah,
  pose saling tak mirip (kemungkinan orang berbeda), atau wajah sudah terdaftar untuk karyawan lain.
- Absen: swafoto absen (file_object yang sama dengan `attendance.face_photo_path`) dicocokkan SERVER dengan embedding
  terdaftar → kemiripan kosinus; skor ×100 disimpan di `attendance.face_match_score`.
  MATCH → lanjut; MISMATCH → absen online ditolak (absen offline ditandai untuk OM); face-service mati/belum diatur
  → UNAVAILABLE: absen tetap tercatat dengan status PENDING_OM.
- Reset pendaftaran oleh pengelola karyawan (manage:users), mis. ganti HP/wajah berubah.
Tidak ada foto wajah pendaftaran yang disimpan; embedding tidak pernah dicatat ke log.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import filetype

from app.core import storage
from app.core.config import settings
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.hard_delete import write_delete_audit
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.face.repositories.face_repository import FaceRepository, parse_embedding
from app.modules.face.schemas.face_schema import EnrollResponse, FacePolicy, FaceStatus
from app.modules.face.services.face_embed_client import EmbedResult, FaceEmbedClient, FaceServiceUnavailable

MATCH_THRESHOLD = 0.80          # kosinus minimum swafoto vs pendaftaran (= skor 80 di attendance)
DUPLICATE_THRESHOLD = 0.80      # pendaftaran yang semirip ini dengan karyawan lain dianggap orang yang sama
POSE_PAIR_MIN = 0.30            # kemiripan TERKECIL antar dua foto pendaftaran (orang sama beda pose ≥ ±0,5)
MIN_ENROLL_QUALITY = 0.30
ENROLL_MIN, ENROLL_MAX = 3, 5
MAX_IMAGE_BYTES = 5 * 1024 * 1024
FIELD_ROLES = ("TEAM_LEADER", "EMPLOYEE")
FAKE_MODEL = "fake-dev"         # penanda model untuk embedding sintetis mode wajah palsu (hanya dev)
FAKE_SIMILARITY = 0.95          # skor yang dikembalikan mode wajah palsu untuk setiap swafoto
EMBED_DIM = 512


def fake_mode_active() -> bool:
    """Mode wajah palsu aktif HANYA di APP_ENV=development (penjaga di config menolak start selain itu)."""
    return bool(settings.FACE_FAKE_MODE) and settings.APP_ENV.strip().lower() == "development"


def fake_embedding(employee_id: object) -> list[float]:
    """Vektor sintetis deterministik per karyawan (dinormalkan). Hanya untuk mode wajah palsu dev."""
    rng = random.Random(hashlib.sha256(f"fake-face:{employee_id}".encode()).digest())
    vector = [rng.gauss(0.0, 1.0) for _ in range(EMBED_DIM)]
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


@dataclass(frozen=True)
class FaceOutcome:
    """Hasil pencocokan swafoto absen."""

    result: str                  # MATCH | MISMATCH | UNAVAILABLE | NOT_ENROLLED | STALE (model berganti)
    similarity: float | None

    @property
    def score(self) -> float:
        """Untuk attendance.face_match_score (0 = tidak diperiksa)."""
        return round(self.similarity * 100.0, 2) if self.similarity is not None else 0.0


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb and len(a) == len(b) else 0.0


def _normalised_mean(vectors: list[list[float]]) -> list[float]:
    mean = [sum(col) / len(vectors) for col in zip(*vectors, strict=True)]
    norm = math.sqrt(sum(v * v for v in mean)) or 1.0
    return [v / norm for v in mean]


def _check_image(image: bytes) -> None:
    if not image:
        raise ValidationError("Gambar wajah kosong.")
    if len(image) > MAX_IMAGE_BYTES:
        raise AppError("FILE_TOO_LARGE", "Ukuran gambar melebihi 5 MB.", status=413)
    kind = filetype.guess(image)
    if kind is None or kind.mime not in ("image/jpeg", "image/png", "image/webp"):
        raise AppError("INVALID_FILE_TYPE", "Gambar wajah harus JPEG, PNG, atau WebP.", status=415)


class FaceService:
    """Pendaftaran & pencocokan wajah."""

    def __init__(self, repo: FaceRepository, client: FaceEmbedClient) -> None:
        self.repo = repo
        self.client = client

    @staticmethod
    def policy() -> FacePolicy:
        return FacePolicy(match_threshold=MATCH_THRESHOLD, enrollment_required=settings.FACE_ENROLLMENT_REQUIRED,
                          min_images=ENROLL_MIN, max_images=ENROLL_MAX)

    async def _employee(self, user_id: str) -> Any:
        employee = await self.repo.employee_of_user(user_id)
        if employee is None:
            raise NotFoundError("Data karyawan")
        return employee

    async def status(self, user_id: str) -> FaceStatus:
        return self._status_of(await self._employee(user_id))

    async def status_of_employee(self, employee_id: UUID) -> FaceStatus:
        """Status wajah karyawan mana pun (dilihat HR/admin lewat detail karyawan)."""
        employee = await self.repo.employee_face_row(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        return self._status_of(employee)

    @staticmethod
    def _status_of(employee: Any) -> FaceStatus:
        vector, meta = parse_embedding(employee.face_embedding)
        enrolled_at = meta.get("enrolled_at")
        return FaceStatus(enrolled=vector is not None, enrolled_at=enrolled_at, model_name=meta.get("model"),
                          required=settings.FACE_ENROLLMENT_REQUIRED and employee.role in FIELD_ROLES)

    async def enroll(self, user_id: str, images: list[bytes]) -> EnrollResponse:
        employee = await self._employee(user_id)
        if employee.role not in FIELD_ROLES:
            raise ForbiddenError("Pendaftaran wajah hanya untuk pekerja lapangan (absen lewat aplikasi HP).")
        if not ENROLL_MIN <= len(images) <= ENROLL_MAX:
            raise ValidationError(f"Unggah {ENROLL_MIN}–{ENROLL_MAX} foto wajah dari sudut berbeda.")
        if parse_embedding(employee.face_embedding)[0] is not None:
            raise AppError("FACE_ALREADY_ENROLLED",
                           "Wajah Anda sudah terdaftar. Minta HR mengatur ulang bila perlu.", status=409)
        if fake_mode_active():  # DEV: tanpa face-service; embedding sintetis deterministik per karyawan
            await self.repo.set_embedding(employee.employee_id, fake_embedding(employee.employee_id), FAKE_MODEL,
                                          "0", jakarta_now())
            return EnrollResponse(enrolled=True, images_used=len(images), quality=None)
        results: list[EmbedResult] = []
        for n, image in enumerate(images, start=1):
            _check_image(image)
            try:
                result = await self.client.embed(image, f"enroll_{n}.jpg")
            except FaceServiceUnavailable:
                raise AppError("FACE_SERVICE_UNAVAILABLE",
                               "Layanan pengenalan wajah sedang tidak tersedia. Coba lagi beberapa saat.",
                               status=503) from None
            except ValueError:
                raise ValidationError(f"Foto ke-{n} tidak bisa dibaca. Ambil ulang.") from None
            if result.faces != 1 or result.embedding is None:
                raise ValidationError(f"Foto ke-{n}: pastikan hanya satu wajah terlihat jelas.")
            if result.quality is not None and result.quality < MIN_ENROLL_QUALITY:
                raise ValidationError(f"Foto ke-{n} kurang jelas (cahaya/fokus). Ambil ulang.")
            results.append(result)
        vectors = [list(r.embedding or []) for r in results]
        if min(cosine(a, b) for i, a in enumerate(vectors) for b in vectors[i + 1:]) < POSE_PAIR_MIN:
            raise ValidationError("Foto-foto tampak bukan orang yang sama. Ambil ulang semua foto wajah Anda.")
        template = _normalised_mean(vectors)
        for other in await self.repo.other_embeddings(employee.employee_id):
            other_vector = parse_embedding(other.face_embedding)[0]
            if other_vector is not None and cosine(template, other_vector) >= DUPLICATE_THRESHOLD:
                raise AppError("FACE_DUPLICATE", "Wajah ini sudah terdaftar untuk karyawan lain. Hubungi HR.",
                               status=409)
        await self.repo.set_embedding(employee.employee_id, template, results[0].model_name,
                                      results[0].model_version, jakarta_now())
        qualities = [r.quality for r in results if r.quality is not None]
        return EnrollResponse(enrolled=True, images_used=len(results),
                              quality=round(min(qualities), 3) if qualities else None)

    async def reset(self, employee_id: UUID, actor: CurrentUser) -> None:
        if not await self.repo.clear_embedding(employee_id):
            raise NotFoundError("Karyawan")
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id, actor_role=actor.role, actor_email=actor.email,
            entity_type="employee", entity_id=employee_id, action="FACE_RESET",
        )

    async def reset_own(self, user_id: str, actor_role: str, actor_email: str) -> UUID:
        """Hapus pendaftaran wajah milik sendiri (idempoten); dicatat di log aktivitas."""
        employee = await self._employee(user_id)
        if parse_embedding(employee.face_embedding)[0] is not None:
            if await self.repo.self_reset_within_day(employee.employee_id):
                raise AppError(
                    "FACE_RESET_LIMIT",
                    "Pendaftaran wajah hanya bisa dihapus sendiri sekali sehari. Coba lagi besok atau hubungi HR.",
                    status=429,
                )
            await self.repo.clear_embedding(employee.employee_id)
            await write_delete_audit(
                self.repo.db,
                actor_user_id=user_id,
                actor_role=actor_role,
                actor_email=actor_email,
                entity_type="employee",
                entity_id=employee.employee_id,
                detail={"reason": "SELF_RESET_FACE"},
                action="FACE_SELF_RESET",
            )
        return UUID(str(employee.employee_id))

    # ── Dipakai modul absensi ─────────────────────────────────────────────────
    async def is_enrolled(self, employee_id: UUID | str) -> bool:
        return parse_embedding(await self.repo.embedding_of(employee_id))[0] is not None

    async def verify_selfie(self, employee_id: UUID | str, selfie_file_id: UUID | str) -> FaceOutcome:
        """Cocokkan swafoto absen (file_object) dengan wajah terdaftar karyawan."""
        template = parse_embedding(await self.repo.embedding_of(employee_id))[0]
        if template is None:
            return FaceOutcome("NOT_ENROLLED", None)
        if fake_mode_active():  # DEV: swafoto apa pun dari karyawan yang terdaftar dianggap cocok
            return FaceOutcome("MATCH", FAKE_SIMILARITY)
        key = await self.repo.file_key(selfie_file_id)
        image = storage.get_image_bytes(key) if key else None
        if not image:
            return FaceOutcome("UNAVAILABLE", None)
        try:
            result = await self.client.embed(image, "selfie.jpg")
        except FaceServiceUnavailable:
            return FaceOutcome("UNAVAILABLE", None)
        except ValueError:
            return FaceOutcome("MISMATCH", 0.0)
        if result.faces != 1 or result.embedding is None:
            return FaceOutcome("MISMATCH", 0.0)
        if len(result.embedding) != len(template):  # didaftarkan dengan model lain → bukan bukti "tidak cocok"
            return FaceOutcome("STALE", None)
        similarity = max(0.0, cosine(list(result.embedding), template))
        return FaceOutcome("MATCH" if similarity >= MATCH_THRESHOLD else "MISMATCH", round(similarity, 4))
