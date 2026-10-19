"""
app/services/attendance_offline_service.py
Absensi lapangan luring (R-34, keputusan pemilik 2026-10-02 — mengubah K-13).

HP merekam absen masuk/pulang saat tanpa sinyal, menandatanganinya dengan kunci Android Keystore (tidak bisa
dikeluarkan dari HP), lalu mengirimnya otomatis begitu online. Server:
1. memverifikasi tanda tangan dengan kunci publik perangkat yang terdaftar → data yang diubah setelah direkam
   (tanggal, jam, lokasi, alasan, swafoto) ditolak;
2. menghitung jam peristiwa dari jangkar waktu bertanda tangan server + penghitung waktu internal Android
   (tidak terpengaruh jam HP), dibandingkan dengan waktu satelit GPS;
3. menerapkan aturan absen yang sama dengan daring (lokasi unit, jarak dihitung trigger, alasan & swafoto wajib);
4. menurunkan status ke Perlu review bila jam tak terverifikasi, terkirim > 24 jam, atau lokasi palsu.
Absen pulang luring: absen masuk valid → langsung tercatat; Perlu review → berlaku saat disetujui; ditolak → gugur.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_der_public_key

from app.core.errors import AppError
from app.core.security import CurrentUser, verify_time_anchor
from app.core.time import utcnow
from app.modules.attendance.repositories.attendance_offline_repository import (
    CRUDAttendanceOffline,
)
from app.modules.attendance.services.attendance_session_service import VALID_STATUSES, AttendanceSessionService

MAX_GPS_DRIFT = timedelta(minutes=5)  # jangkar vs waktu satelit GPS
MAX_FUTURE = timedelta(minutes=2)
SYNC_DEADLINE = timedelta(hours=24)  # keputusan pemilik: lewat 24 jam → Perlu review
HARD_LIMIT = timedelta(days=7)  # lebih lama dari ini tidak diterima sama sekali


def _reject(code: str, message: str, status: int = 422) -> AppError:
    return AppError(code, message, status=status)


class AttendanceOfflineService:
    """Layanan untuk mengelola absensi luring (offline) yang disinkronisasi ketika perangkat kembali daring (online)."""

    def __init__(self, repo: CRUDAttendanceOffline, sessions: AttendanceSessionService) -> None:
        self.repo = repo
        self.sessions = sessions

    async def register_device_key(self, user: CurrentUser, device_id: str, public_key: str) -> None:
        """
        Mendaftarkan kunci publik (public key) perangkat keras (Android Keystore)
        untuk validasi tanda tangan kriptografis.

        Args:
            user: Pengguna yang melakukan pendaftaran.
            device_id: ID unik perangkat.
            public_key: String base64 kunci publik ECDSA.
        """
        try:
            key = load_der_public_key(base64.b64decode(public_key))
        except ValueError as exc:
            raise _reject(
                "DEVICE_KEY_INVALID",
                "Pendaftaran perangkat untuk absen luring gagal. Perbarui aplikasi, lalu coba lagi saat online.",
            ) from exc
        if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
            raise _reject(
                "DEVICE_KEY_INVALID",
                "Perangkat ini belum dapat dipakai untuk absen luring. Perbarui aplikasi, lalu buka saat online.",
            )
        await self.repo.register_device_key(user.organization_id, user.user_id, device_id, public_key)

    async def _verified_payload(
        self, user: CurrentUser, device_id: str, payload: str, signature: str
    ) -> dict[str, Any]:
        """
        Memverifikasi tanda tangan kriptografis pada payload (data absensi) dari perangkat.
        Pencegahan agar data waktu dan lokasi tidak dimanipulasi di sisi klien.
        """
        public_key = await self.repo.device_key(user.user_id, device_id)
        if public_key is None:
            raise _reject(
                "DEVICE_KEY_MISSING",
                "Perangkat belum terdaftar untuk absen luring. Buka aplikasi saat online sekali, lalu kirim ulang.",
                status=409,
            )
        key = load_der_public_key(base64.b64decode(public_key))
        assert isinstance(key, ec.EllipticCurvePublicKey)
        try:
            # Memastikan integritas data menggunakan kurva secp256r1 dan hash SHA-256.
            key.verify(base64.b64decode(signature), payload.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
        except (InvalidSignature, ValueError) as exc:
            raise _reject(
                "OFFLINE_TAMPERED",
                "Data absen luring tidak utuh — tanggal, jam, atau lokasi diubah setelah direkam. Absen ditolak.",
            ) from exc
        data: dict[str, Any] = json.loads(payload)
        if data.get("device_id") != device_id:
            raise _reject("OFFLINE_TAMPERED", "Data absen luring bukan dari perangkat ini.")
        return data

    def _event_time(self, user: CurrentUser, p: dict[str, Any]) -> tuple[datetime, bool, list[str]]:
        """
        Menghitung dan memvalidasi waktu absensi (jam peristiwa) menggunakan mekanisme jangkar waktu (time anchor)
        untuk melawan manipulasi jam perangkat lokal.

        Returns:
            Tuple dari (jam peristiwa, terverifikasi (boolean), daftar alasan perlu review).
        """
        notes: list[str] = []
        anchor_ms = verify_time_anchor(str(p.get("anchor_token") or ""), user.user_id)
        same_boot = p.get("anchor_boot_count") == p.get("event_boot_count")
        elapsed = int(p.get("event_elapsed_ms", 0)) - int(p.get("anchor_elapsed_ms", 0))
        gps_ms = p.get("gps_time_ms")
        if anchor_ms is not None and same_boot and elapsed >= 0:
            event = datetime.fromtimestamp((anchor_ms + elapsed) / 1000, tz=UTC)
            gps_ok = (
                gps_ms is not None and abs(int(gps_ms) - (anchor_ms + elapsed)) <= MAX_GPS_DRIFT.total_seconds() * 1000
            )
            trusted = gps_ok
            if not gps_ok:
                notes.append("jam tidak cocok dengan waktu satelit GPS")
        elif gps_ms is not None:
            # HP dinyalakan ulang saat luring / jangkar tak ada: hanya waktu satelit GPS → perlu review.
            event = datetime.fromtimestamp(int(gps_ms) / 1000, tz=UTC)
            trusted = False
            notes.append("jam hanya dari satelit GPS (HP dinyalakan ulang saat luring)")
        else:
            raise _reject("OFFLINE_TIME_UNKNOWN", "Jam absen luring tidak dapat dipastikan. Absen ditolak.")
        now = utcnow()
        if event > now + MAX_FUTURE:
            raise _reject("OFFLINE_TIME_UNKNOWN", "Jam absen luring berada di masa depan. Absen ditolak.")
        if now - event > HARD_LIMIT:
            raise _reject("OFFLINE_TOO_OLD", "Absen luring lebih dari 7 hari tidak dapat diterima.")
        if now - event > SYNC_DEADLINE:
            notes.append("terkirim lebih dari 24 jam setelah absen")
        if p.get("mocked"):
            notes.append("lokasi palsu terdeteksi")
        return event, trusted, notes

    async def apply(
        self,
        user: CurrentUser,
        *,
        device_id: str,
        client_op_id: UUID,
        kind: str,
        payload: str,
        signature: str,
        selfie_file_id: UUID | None,
        face_probe_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Memproses sinkronisasi data absensi (masuk/pulang) yang dikumpulkan saat perangkat luring.

        Args:
            user: Pengguna yang melakukan absensi.
            device_id: ID perangkat.
            client_op_id: ID unik operasi klien untuk idempotency.
            kind: Jenis operasi ("CHECK_IN" atau "CHECK_OUT").
            payload: Data absensi asli dalam format JSON string.
            signature: Tanda tangan digital atas payload.
            selfie_file_id: ID file foto swafoto jika ada.

        Returns:
            Status penerapan data absensi luring.
        """
        # Idempotency: Jika client_op_id sudah ada, kembalikan hasil sebelumnya
        # (menghindari proses ganda saat ada percobaan ulang koneksi jaringan).
        done = await self.repo.event(client_op_id)
        if done is not None:
            if str(done.user_id) != user.user_id:
                raise _reject(
                    "OFFLINE_TAMPERED",
                    "Data absen luring tidak dikenali. Perbarui aplikasi, lalu kirim ulang.",
                    status=404,
                )
            return {
                "client_op_id": client_op_id,
                "result": done.result,
                "attendance_id": done.attendance_id,
                "duplicate": True,
            }
        p = await self._verified_payload(user, device_id, payload, signature)
        if p.get("client_op_id") != str(client_op_id) or p.get("kind") != kind:
            raise _reject("OFFLINE_TAMPERED", "Data absen luring tidak cocok dengan kirimannya.")

        # Mengekstrak dan memverifikasi waktu absensi secara ketat melawan manipulasi jam perangkat.
        event, trusted, notes = self._event_time(user, p)
        # Pengenalan wajah: blok `face` ikut ditandatangani HP (termasuk hash gambar wajah sementara).
        face = p.get("face") if isinstance(p.get("face"), dict) else None
        if face is not None and face_probe_id is None:
            raise _reject("OFFLINE_FACE_MISSING", "Gambar wajah absen luring belum terunggah.")

        if kind == "CHECK_IN":
            result, attendance_id = await self._check_in(user, p, event, notes, selfie_file_id, face_probe_id, face)
        else:
            result, attendance_id = await self._check_out(user, event, notes, face_probe_id, face, p)

        await self.repo.record_event(
            client_op_id=client_op_id,
            org_id=user.organization_id,
            user_id=user.user_id,
            kind=kind,
            attendance_id=attendance_id,
            event_time=event,
            time_trusted=trusted,
            result=result,
        )
        return {
            "client_op_id": client_op_id,
            "result": result,
            "attendance_id": attendance_id,
            "duplicate": False,
            "event_time": event,
            "time_trusted": trusted,
            "notes": notes,
        }

    @staticmethod
    def _face_notes(face: dict[str, Any] | None, server_result: str | None, notes: list[str]) -> None:
        """Hasil HP hanya pendamping: yang berlaku hitungan server. Selisih besar = kemungkinan manipulasi."""
        if face is None or server_result is None:
            return
        local = face.get("local_result")
        if local == "MATCH" and server_result in ("NO_MATCH", "LOW_QUALITY"):
            notes.append("wajah cocok di HP tetapi tidak cocok di server (kemungkinan manipulasi)")
        elif server_result == "NO_MATCH":
            notes.append("wajah tidak cocok")
        elif server_result == "LOW_QUALITY":
            notes.append("pemeriksaan keaslian wajah tidak lolos")

    async def _check_in(
        self,
        user: CurrentUser,
        p: dict[str, Any],
        event: datetime,
        notes: list[str],
        selfie_file_id: UUID | None,
        face_probe_id: UUID | None = None,
        face: dict[str, Any] | None = None,
    ) -> tuple[str, Any]:
        """
        Memproses data absensi masuk (check-in) yang tertunda saat luring.
        Memvalidasi keberadaan dan kecocokan swafoto dengan hash yang direkam saat luring.
        """
        expected_sha = p.get("selfie_sha256")
        if expected_sha:
            if selfie_file_id is None:
                raise _reject("OFFLINE_SELFIE_MISSING", "Swafoto absen luring belum terunggah.")
            actual = await self.repo.file_sha256(selfie_file_id, user.organization_id)
            if actual is None or actual.lower() != str(expected_sha).lower():
                raise _reject("OFFLINE_TAMPERED", "Swafoto absen luring tidak sama dengan yang direkam.")
        work_date = await self.repo.local_date(user.organization_id, event)
        row = await self.sessions.check_in(
            user.organization_id,
            user.user_id,
            site_id=UUID(str(p["site_id"])),
            lng=float(p["lng"]),
            lat=float(p["lat"]),
            origin="GPS",
            accuracy_m=p.get("accuracy_m"),
            selfie_file_id=selfie_file_id if expected_sha else None,
            channel="MOBILE",
            explanation=p.get("explanation"),
            at=event,
            work_date=work_date,
            face_probe_id=face_probe_id if face is not None else None,
            online=False,
            expected_face_sha256=str(face.get("probe_sha256") or "") if face is not None else None,
        )
        self._face_notes(face, getattr(row, "face_result", None), notes)
        note = "; ".join(notes) if notes else None
        marked = await self.repo.mark_offline(row.id, note, force_review=bool(notes))
        return str(marked.status), marked.id

    async def _check_out(
        self,
        user: CurrentUser,
        event: datetime,
        notes: list[str],
        face_probe_id: UUID | None = None,
        face: dict[str, Any] | None = None,
        p: dict[str, Any] | None = None,
    ) -> tuple[str, Any]:
        """
        Memproses data absensi pulang (check-out) yang tertunda saat luring. Lokasi pulang ikut disimpan; di luar
        radius tidak ditolak (sudah terjadi) melainkan ditandai Perlu review oleh trigger (T7).
        """
        worker = await self.sessions.repo.attendance_mode_of(user.user_id)
        if worker is None or worker.attendance_mode != "FIELD":
            raise _reject("WRONG_ATTENDANCE_CHANNEL", "Absen luring hanya untuk pekerja lapangan.", status=403)
        target = await self.repo.open_before(worker.employee_id, event)
        if target is None:
            raise _reject("NO_OPEN_SESSION", "Tidak ada absen masuk yang bisa ditutup untuk jam ini.", status=409)
        if target.status in VALID_STATUSES:
            lat, lng = (p or {}).get("lat"), (p or {}).get("lng")
            await self.repo.close_at(
                target.id,
                event,
                lat=float(lat) if lat is not None else None,
                lng=float(lng) if lng is not None else None,
            )
            result = "CHECKED_OUT"
        else:
            await self.repo.request_checkout(target.id, event)
            result = "CHECK_OUT_PENDING_REVIEW"
        row = await self.sessions.apply_face(
            user.organization_id,
            user.user_id,
            target,
            "CHECK_OUT",
            face_probe_id if face is not None else None,
            online=False,
            expected_sha256=str(face.get("probe_sha256") or "") if face is not None else None,
            device="MOBILE",
        )
        if face is not None:
            self._face_notes(face, getattr(row, "check_out_face_result", None), notes)
        return result, target.id
