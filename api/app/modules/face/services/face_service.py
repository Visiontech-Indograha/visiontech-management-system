"""
app/services/face_service.py
Aturan pengenalan wajah untuk absensi HP (docs/06 fase 8, docs/08 §6).

Prinsip yang dijaga di sini:
- Yang disimpan embedding, bukan foto. Gambar wajah sementara (probe) bukan foto absensi: tidak tampil di riwayat,
  dihapus sesuai `organization.face_probe_retention_days`.
- Persetujuan biometrik wajib dan bisa ditarik kapan saja (trigger DB menonaktifkan embedding seketika).
- Hasil cocok/tidak dihitung SERVER dari gambar yang diterima (aturan inti #3); hasil dari HP hanya pendamping.
- Hasil bermasalah menandai absensi untuk diperiksa manusia, bukan menolak diam-diam.
- face-service mati → absen tetap berjalan (hasil SKIPPED), diperiksa ulang saat layanan pulih.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta
from time import monotonic
from typing import Any

import filetype

from app.core.config import settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import create_face_challenge_proof, verify_face_challenge_proof
from app.core.storage import delete_object, get_object_bytes, upload_file
from app.core.time import utcnow
from app.modules.face.repositories.face_repository import CRUDFace, parse_vector
from app.modules.face.schemas.face_schema import (
    ChallengeCheckResponse,
    ConsentRequest,
    EnrollResponse,
    FaceLiveness,
    FacePolicy,
    FaceStatus,
    ProbeResponse,
    TemplateResponse,
)
from app.services.face_embed_client import EmbedResult, FaceEmbedClient, FaceServiceUnavailable

logger = logging.getLogger(__name__)

POLICY_VERSION = "2026-10-05"
POLICY_TEXT = (
    "Saya menyetujui PT Visiontech memakai data wajah saya HANYA untuk absensi masuk dan pulang. "
    "Yang disimpan adalah data numerik wajah (bukan foto) dan gambar wajah sementara yang dihapus otomatis "
    "setelah masa simpan yang ditetapkan perusahaan. Data ini hanya dapat dibaca oleh saya, HR, dan proses "
    "pencocokan; tidak untuk pelaporan atau tujuan lain. Saya boleh menarik persetujuan kapan saja dan data "
    "wajah saya langsung dinonaktifkan. Bila saya menolak atau menarik persetujuan, saya tetap bisa absen "
    "tanpa pengenalan wajah dan tidak dirugikan."
)
WITHDRAW_TEXT = "Persetujuan biometrik ditarik oleh karyawan."

ENROLL_MIN, ENROLL_MAX = 3, 5
MIN_ENROLL_QUALITY = 0.30  # skor kualitas face-service (deteksi x ukuran x ketajaman); dikalibrasi di P8-5
MIN_PROBE_QUALITY = 0.15  # di bawah ini diminta ulang; di atasnya dinilai server (LOW_QUALITY/NO_MATCH)
# Kemiripan TERKECIL antar dua pose. Bukan "pose terhadap rata-rata": untuk wajah berbeda yang saling tegak lurus nilai
# itu tetap ±0,58 (3 pose) / ±0,45 (5 pose) sehingga pemeriksaannya tak pernah menolak. Orang sama beda pose ≥ ±0,5;
# orang berbeda ≈ 0-0,2. Titik awal; dikalibrasi di P8-5 dengan data nyata.
POSE_PAIR_MIN = 0.30
MAX_IMAGE_BYTES = 5 * 1024 * 1024
TEMPLATE_RATE = (10, 3600.0)  # maksimal 10 unduhan template per jam per pengguna
CHALLENGE_RATE = (
    1200,
    600.0,
)  # ±2 bingkai/detik selama 10 menit (HP mengirim tiap 0,3–0,45 dtk); menahan penyalahgunaan CPU face-service
CHALLENGES = ("depan", "kiri", "kanan", "atas", "bawah", "buka_mulut")
NO_PROOF_CHALLENGES = ("depan",)  # hanya panduan meluruskan wajah; TIDAK menerbitkan bukti liveness
LIVENESS_PROOFS_REQUIRED = 2  # tantangan BERBEDA yang harus dibuktikan server untuk absen online & pendaftaran
_template_hits: dict[str, deque[float]] = defaultdict(deque)
_challenge_hits: dict[str, deque[float]] = defaultdict(deque)

NEEDS_REVIEW_RESULTS = ("NO_MATCH", "LOW_QUALITY")


@dataclass(frozen=True)
class FaceOutcome:
    """Hasil pencocokan wajah untuk satu absen (masuk/pulang)."""

    result: str
    similarity: float | None
    check_id: Any
    note: str
    flag_review: bool
    pending: bool = False


def _unavailable() -> AppError:
    return AppError(
        "FACE_SERVICE_UNAVAILABLE",
        "Layanan pengenalan wajah sedang tidak tersedia. Coba lagi beberapa saat.",
        status=503,
    )


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _version(rows: list[Any]) -> str | None:
    """Versi pendaftaran: berubah setiap pendaftaran ulang (HP memakainya untuk memperbarui template)."""
    if not rows:
        return None
    newest = max(r.captured_at for r in rows)
    return f"{len(rows)}-{int(newest.timestamp())}"


class FaceService:
    """Persetujuan, pendaftaran, template untuk HP, gambar wajah sementara, dan pencocokan 1:1."""

    def __init__(self, repo: CRUDFace, client: FaceEmbedClient) -> None:
        self.repo = repo
        self.client = client

    # ── Status & persetujuan ────────────────────────────────────────────────────────────────────
    def policy(self) -> FacePolicy:
        return FacePolicy(version=POLICY_VERSION, text=POLICY_TEXT)

    async def _employee(self, user_id: str, *, field_only: bool = False) -> Any:
        """Karyawan milik akun. Pengenalan wajah berlaku untuk SEMUA karyawan: lapangan lewat HP (boleh luring),
        kantor lewat web (hanya online). `field_only` dipertahankan agar pemanggil lama tetap valid."""
        row = await self.repo.employee_of_user(user_id)
        if row is None:
            raise ValidationError("Akun ini belum tertaut ke data karyawan.")
        return row

    async def status(self, org_id: str, user_id: str, *, exempt_from_required: bool = False) -> FaceStatus:
        org = await self.repo.org_settings(org_id)
        liveness_required = bool(org.face_liveness_required) if org else True
        employee = await self.repo.employee_of_user(user_id)
        if employee is None:
            return FaceStatus(
                employee_linked=False,
                liveness_required=liveness_required,
                template_ttl_days=settings.FACE_TEMPLATE_TTL_DAYS,
                policy=self.policy(),
            )
        consent = await self.repo.latest_consent(employee.employee_id)
        rows = (
            list(await self.repo.active_enrollments(employee.employee_id))
            if (consent and consent.state == "GRANTED")
            else []
        )
        return FaceStatus(
            employee_linked=True,
            consent=consent.state if consent else None,
            consent_policy_version=consent.policy_version if consent else None,
            enrolled=bool(rows),
            enrollment_version=_version(rows),
            model_name=rows[0].model_name if rows else None,
            model_version=rows[0].model_version if rows else None,
            liveness_required=liveness_required,
            # Administrator tidak pernah dikunci gerbang pendaftaran (jalur darurat bila layanan wajah bermasalah).
            enrollment_required=settings.FACE_ENROLLMENT_REQUIRED and not rows and not exempt_from_required,
            template_ttl_days=settings.FACE_TEMPLATE_TTL_DAYS,
            policy=self.policy(),
        )

    async def set_consent(self, user_id: str, body: ConsentRequest) -> None:
        employee = await self._employee(user_id)
        if body.state == "GRANTED":
            if body.policy_version != POLICY_VERSION:
                raise AppError(
                    "POLICY_OUTDATED",
                    "Teks persetujuan sudah diperbarui. Muat ulang lalu baca kembali sebelum menyetujui.",
                    status=409,
                )
            await self.repo.record_consent(employee.employee_id, "GRANTED", POLICY_TEXT, POLICY_VERSION, user_id)
        else:
            # Trigger DB menonaktifkan seluruh embedding seketika; gambar sementara dihapus oleh retensi.
            await self.repo.record_consent(employee.employee_id, "WITHDRAWN", WITHDRAW_TEXT, POLICY_VERSION, user_id)

    async def _verified_liveness(
        self, employee_id: Any, user_id: str, liveness: FaceLiveness
    ) -> tuple[bool, list[str], list[str]]:
        """
        Liveness yang DIPERCAYA server: bukti tantangan bertanda tangan (sah, milik pengguna ini, belum kedaluwarsa,
        belum pernah dipakai, tantangan berbeda). → (lolos, tantangan terbukti, nonce). Klaim `passed` dari HP tidak
        dihitung di sini; ia hanya berlaku untuk absen luring.
        """
        challenges: list[str] = []
        nonces: list[str] = []
        for token in liveness.proofs:
            proof = verify_face_challenge_proof(token, user_id)
            if proof is None or proof[0] in challenges or proof[1] in nonces:
                continue
            challenges.append(proof[0])
            nonces.append(proof[1])
        if nonces:
            reused = await self.repo.used_proof_nonces(employee_id, nonces)
            kept = [(c, n) for c, n in zip(challenges, nonces, strict=True) if n not in reused]
            challenges, nonces = [c for c, _ in kept], [n for _, n in kept]
        return len(challenges) >= LIVENESS_PROOFS_REQUIRED, challenges, nonces

    async def face_expected(self, user_id: str) -> bool:
        """
        Karyawan (lapangan maupun kantor) yang sudah menyetujui & mendaftar wajah:
        absennya WAJIB membawa data wajah.
        """
        employee = await self.repo.employee_of_user(user_id)
        if employee is None:
            return False
        return await self.repo.face_expected(employee.employee_id)

    async def _require_consent(self, employee_id: Any) -> None:
        consent = await self.repo.latest_consent(employee_id)
        if consent is None or consent.state != "GRANTED":
            raise AppError("CONSENT_REQUIRED", "Setujui pemakaian data wajah terlebih dahulu.", status=409)

    # ── Pendaftaran ─────────────────────────────────────────────────────────────────────────────
    async def _embed(self, image: bytes, name: str) -> EmbedResult:
        try:
            return await self.client.embed(image, name)
        except FaceServiceUnavailable:
            raise _unavailable() from None
        except ValueError:
            raise ValidationError("Gambar wajah tidak dapat dibaca. Ulangi foto wajah.") from None

    async def enroll(self, org_id: str, user_id: str, images: list[bytes], liveness: FaceLiveness) -> EnrollResponse:
        employee = await self._employee(user_id, field_only=True)
        await self._require_consent(employee.employee_id)
        if not ENROLL_MIN <= len(images) <= ENROLL_MAX:
            raise ValidationError(f"Pendaftaran wajah butuh {ENROLL_MIN} sampai {ENROLL_MAX} foto berpose berbeda.")
        org = await self.repo.org_settings(org_id)
        verified, _, _ = await self._verified_liveness(employee.employee_id, user_id, liveness)
        if org.face_liveness_required and not verified:
            raise ValidationError("Tantangan keaslian wajah belum lolos. Ulangi pendaftaran.")

        results: list[EmbedResult] = []
        for index, image in enumerate(images, start=1):
            self._check_image(image)
            result = await self._embed(image, f"pose{index}.jpg")
            if result.faces == 0 or (result.faces == 1 and result.embedding is None):
                raise ValidationError(f"Foto ke-{index}: wajah tidak terdeteksi. Hadap kamera dengan jelas.")
            if result.faces > 1:
                raise ValidationError(f"Foto ke-{index}: terdeteksi lebih dari satu wajah.")
            if (result.quality or 0) < MIN_ENROLL_QUALITY:
                raise ValidationError(f"Foto ke-{index}: terlalu buram, gelap, atau wajah terlalu jauh. Ulangi.")
            results.append(result)

        vectors = [_normalize(r.embedding or []) for r in results]
        mean = _normalize([sum(col) / len(vectors) for col in zip(*vectors, strict=True)])
        if min(_cosine(a, b) for i, a in enumerate(vectors) for b in vectors[i + 1 :]) < POSE_PAIR_MIN:
            raise ValidationError("Foto-foto tampak bukan wajah yang sama. Ulangi dengan wajah Anda sendiri.")
        other = await self.repo.best_other_similarity(org_id, employee.employee_id, mean)
        if other is not None and other >= float(org.face_match_threshold):
            raise AppError(
                "FACE_ALREADY_ENROLLED", "Wajah ini sudah terdaftar untuk karyawan lain. Hubungi HR.", status=409
            )

        await self.repo.deactivate_enrollments(employee.employee_id, "Pendaftaran ulang")
        for vec, res in zip(vectors, results, strict=True):
            await self.repo.insert_enrollment(
                org_id, employee.employee_id, vec, res.model_name, res.model_version, res.quality, user_id
            )
        rows = list(await self.repo.active_enrollments(employee.employee_id))
        return EnrollResponse(
            enrolled=len(rows),
            enrollment_version=_version(rows) or "",
            model_name=results[0].model_name,
            model_version=results[0].model_version,
        )

    # ── Template untuk HP (pencocokan luring) ───────────────────────────────────────────────────
    @staticmethod
    def _throttle(bucket: dict[str, deque[float]], rate: tuple[int, float], key: str, message: str) -> None:
        limit, window = rate
        now = monotonic()
        hits = bucket[key]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            raise AppError("TOO_MANY_REQUESTS", message, status=429)
        hits.append(now)

    def _rate_limit(self, user_id: str) -> None:
        self._throttle(
            _template_hits, TEMPLATE_RATE, user_id, "Terlalu sering mengunduh template wajah. Coba lagi nanti."
        )

    async def template(self, user_id: str) -> TemplateResponse:
        employee = await self._employee(user_id, field_only=True)
        await self._require_consent(employee.employee_id)
        rows = list(await self.repo.active_enrollments(employee.employee_id))
        if not rows:
            raise AppError("NOT_ENROLLED", "Wajah belum terdaftar.", status=404)
        self._rate_limit(user_id)
        logger.info("Template wajah diunduh pemilik (jumlah pose %d)", len(rows))  # tanpa isi embedding
        return TemplateResponse(
            model_name=rows[0].model_name,
            model_version=rows[0].model_version,
            enrollment_version=_version(rows) or "",
            embeddings=[parse_vector(r.embedding) or [] for r in rows],
            expires_at=utcnow() + timedelta(days=settings.FACE_TEMPLATE_TTL_DAYS),
        )

    # ── Gambar wajah sementara (probe) ──────────────────────────────────────────────────────────
    async def check_challenge(self, user_id: str, image: bytes, challenge: str) -> ChallengeCheckResponse:
        """Memeriksa satu bingkai kamera terhadap tantangan liveness (online). Layanan mati → 503, TIDAK pernah
        'sukses' otomatis: tantangan yang lolos tanpa pemeriksaan sama dengan tanpa liveness."""
        if challenge not in CHALLENGES:
            raise ValidationError("Pemeriksaan keaslian wajah tidak dikenali. Ulangi pengenalan wajah.")
        self._check_image(image)
        self._throttle(
            _challenge_hits,
            CHALLENGE_RATE,
            user_id,
            "Terlalu banyak pemeriksaan tantangan. Tunggu sebentar lalu ulangi.",
        )
        try:
            res = await self.client.check_challenge(image, challenge)
        except FaceServiceUnavailable:
            raise _unavailable() from None
        except ValueError as ve:
            return ChallengeCheckResponse(status="menunggu", detail=str(ve))
        passed = res.get("status") == "sukses"
        return ChallengeCheckResponse(
            status="sukses" if passed else "menunggu",
            detail=str(res.get("detail", "")),
            quality=res.get("quality"),
            proof=(
                create_face_challenge_proof(user_id, challenge)
                if passed and challenge not in NO_PROOF_CHALLENGES
                else None
            ),
            metrics=res.get("metrics") if settings.APP_ENV == "development" else None,
        )

    @staticmethod
    def _check_image(image: bytes) -> str:
        if not image:
            raise ValidationError("Gambar kosong.")
        if len(image) > MAX_IMAGE_BYTES:
            raise AppError("FILE_TOO_LARGE", "Ukuran gambar melebihi 5 MB.", status=413)
        kind = filetype.guess(image)
        if kind is None or kind.mime not in ("image/jpeg", "image/png"):
            raise AppError("INVALID_FILE_TYPE", "Gambar wajah harus JPEG atau PNG.", status=415)
        return str(kind.extension)

    async def create_probe(self, org_id: str, user_id: str, image: bytes, liveness: FaceLiveness) -> ProbeResponse:
        employee = await self._employee(user_id, field_only=True)
        await self._require_consent(employee.employee_id)
        ext = self._check_image(image)
        embedding: EmbedResult | None
        try:
            embedding = await self.client.embed(image, f"probe.{ext}")
        except FaceServiceUnavailable:
            embedding = None  # absen tetap bisa: disimpan, dihitung & diperiksa ulang saat layanan pulih
        except ValueError:
            raise ValidationError("Gambar wajah tidak dapat dibaca. Ulangi foto wajah.") from None
        if embedding is not None:
            if embedding.faces == 0:
                raise ValidationError("Wajah tidak terdeteksi. Hadap kamera dengan wajah terlihat jelas.")
            if embedding.faces > 1:
                raise ValidationError("Terdeteksi lebih dari satu wajah. Pastikan hanya Anda di kamera.")
            if (embedding.quality or 0) < MIN_PROBE_QUALITY:
                raise ValidationError("Gambar terlalu buram atau gelap, atau wajah terlalu jauh. Ulangi.")

        verified, verified_challenges, nonces = await self._verified_liveness(employee.employee_id, user_id, liveness)
        file_id = uuid.uuid4()
        probe_id = uuid.uuid4()
        digest = hashlib.sha256(image).digest()  # byte ASLI (tanpa kompresi): dicocokkan dengan payload luring
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        key = f"{org_id}/face-probe/{file_id}.{ext}"
        await self.repo.insert_file_object(
            file_id=file_id,
            org_id=org_id,
            storage_key=key,
            name=f"probe.{ext}",
            mime=mime,
            size=len(image),
            sha256=digest,
            user_id=user_id,
        )
        row = await self.repo.insert_probe(
            probe_id=probe_id,
            org_id=org_id,
            employee_id=employee.employee_id,
            embedding=embedding.embedding if embedding else None,
            model_name=embedding.model_name if embedding else None,
            model_version=embedding.model_version if embedding else None,
            quality=embedding.quality if embedding else None,
            liveness={
                "challenges": liveness.challenges,
                "passed": liveness.passed,  # klaim HP (hanya absen luring)
                "server_verified": verified,
                "verified_challenges": verified_challenges,
                "proof_nonces": nonces,
            },
            file_id=file_id,
            sha256=digest,
        )
        loop = asyncio.get_running_loop()
        if not await loop.run_in_executor(None, upload_file, key, image, mime):
            raise AppError(
                "STORAGE_UNAVAILABLE", "Penyimpanan berkas sedang tidak tersedia. Coba lagi beberapa saat.", status=503
            )
        return ProbeResponse(
            probe_id=probe_id,
            quality=embedding.quality if embedding else None,
            pending=embedding is None,
            expires_at=row.created_at + timedelta(minutes=settings.FACE_PROBE_MAX_AGE_MIN),
        )

    # ── Pencocokan untuk absen ──────────────────────────────────────────────────────────────────
    async def verify_for_attendance(
        self,
        org_id: str,
        user_id: str,
        *,
        probe_id: uuid.UUID,
        event: str,
        attendance_id: Any,
        device: str | None = None,
        online: bool = True,
        expected_sha256: str | None = None,
    ) -> FaceOutcome:
        """
        Mencocokkan gambar wajah sementara dengan pendaftaran pemilik akun (1:1, di basis data).

        `online`: absen langsung (probe harus baru). Luring: terikat payload bertanda tangan lewat
        `expected_sha256` (hash byte yang dicatat HP saat merekam) — bukan umur probe.
        """
        employee = await self._employee(user_id)
        probe = await self.repo.get_probe(probe_id)
        # RLS menyembunyikan milik orang lain; cek eksplisit tetap perlu untuk HR/ADMIN yang melihat semuanya.
        if probe is None or str(probe.employee_id) != str(employee.employee_id) or str(probe.organization_id) != org_id:
            raise NotFoundError("Gambar wajah")
        if probe.consumed_at is not None:
            raise AppError("PROBE_USED", "Gambar wajah ini sudah dipakai. Ulangi pengenalan wajah.", status=409)
        if online and utcnow() - probe.created_at > timedelta(minutes=settings.FACE_PROBE_MAX_AGE_MIN):
            raise AppError("PROBE_EXPIRED", "Gambar wajah sudah kedaluwarsa. Ulangi pengenalan wajah.", status=409)
        if expected_sha256 is not None and bytes(probe.sha256).hex() != expected_sha256.lower():
            raise AppError("OFFLINE_TAMPERED", "Gambar wajah tidak sama dengan yang direkam di HP.", status=422)

        # Online: hanya liveness yang dibuktikan server. Luring: klaim HP diterima (tidak ada server saat itu); sidik
        # hash gambar terikat payload bertanda tangan dan hasilnya tetap dihitung ulang server.
        stored = probe.liveness or {}
        liveness_ok = bool(stored.get("server_verified")) or (not online and bool(stored.get("passed")))
        await self.repo.consume_probe(probe_id, event, attendance_id, liveness_ok)
        embedding = parse_vector(probe.embedding)
        if embedding is None:
            return FaceOutcome(
                "SKIPPED",
                None,
                None,
                "Layanan pengenalan wajah sedang tidak tersedia; wajah diperiksa ulang nanti.",
                flag_review=False,
                pending=True,
            )
        verdict = await self.repo.verify(
            org_id=org_id,
            employee_id=employee.employee_id,
            embedding=embedding,
            liveness=1.0 if liveness_ok else 0.0,
            probe_file_id=probe.file_id,
            device=device,
            event=event,
        )
        await self.repo.link_check(verdict.check_id, attendance_id)
        return FaceOutcome(
            str(verdict.result),
            None if verdict.similarity is None else float(verdict.similarity),
            verdict.check_id,
            str(verdict.note),
            str(verdict.result) in NEEDS_REVIEW_RESULTS,
        )

    # ── Penjadwal (token ADMIN) ─────────────────────────────────────────────────────────────────
    async def recompute_pending(self, limit: int = 50) -> tuple[list[tuple[Any, str, FaceOutcome]], int]:
        """
        Menghitung embedding probe yang tertunda (face-service mati saat absen) lalu mencocokkannya.
        Mengembalikan ([(attendance_id, event, hasil)], jumlah yang masih tertunda).
        """
        done: list[tuple[Any, str, FaceOutcome]] = []
        loop = asyncio.get_running_loop()
        rows = list(await self.repo.pending_probes(limit))
        for probe in rows:
            image = await loop.run_in_executor(None, get_object_bytes, probe.storage_key)
            if image is None:
                continue
            try:
                result = await self.client.embed(image, "probe.jpg")
            except FaceServiceUnavailable:
                break  # layanan masih mati; coba lagi pada putaran berikut
            except ValueError:
                continue
            if result.faces != 1 or result.embedding is None:
                continue
            await self.repo.set_probe_embedding(
                probe.id, result.embedding, result.model_name, result.model_version, result.quality
            )
            passed = bool((probe.liveness or {}).get("effective_passed"))  # putusan terkunci saat absen dicatat
            verdict = await self.repo.verify(
                org_id=probe.organization_id,
                employee_id=probe.employee_id,
                embedding=result.embedding,
                liveness=1.0 if passed else 0.0,
                probe_file_id=probe.file_id,
                device="reverify",
                event=probe.consumed_event,
            )
            await self.repo.link_check(verdict.check_id, probe.attendance_id)
            done.append(
                (
                    probe.attendance_id,
                    str(probe.consumed_event),
                    FaceOutcome(
                        str(verdict.result),
                        None if verdict.similarity is None else float(verdict.similarity),
                        verdict.check_id,
                        str(verdict.note),
                        str(verdict.result) in NEEDS_REVIEW_RESULTS,
                    ),
                )
            )
        return done, max(0, len(rows) - len(done))

    async def purge_expired(self) -> int:
        """Hapus gambar wajah yang lewat masa simpan: objek MinIO dulu, lalu baris basis data."""
        loop = asyncio.get_running_loop()
        for row in await self.repo.expired_files():
            if not await loop.run_in_executor(None, delete_object, row.storage_key):
                logger.warning("Objek gambar wajah gagal dihapus dari penyimpanan; baris tetap dibersihkan.")
        return await self.repo.purge()
