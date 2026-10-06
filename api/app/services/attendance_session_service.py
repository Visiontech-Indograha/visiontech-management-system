"""
app/services/attendance_session_service.py
Aturan absensi (V-12) — padanan `domain.js` CHECK_IN, CHECK_OUT, EXPLAIN_ATTENDANCE, REVIEW_ATTENDANCE.
Tanggal & jam dari server menurut zona waktu organisasi (V-10); jarak/status/terlambat/pulang cepat
diputuskan trigger basis data, dan hasil simpanan itulah yang dikembalikan ke klien.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError, trigger_rule_message
from app.crud.crud_attendance_session import CRUDAttendanceSession
from app.crud.crud_org_clock import CRUDOrgClock
from app.services.face_service import FaceOutcome, FaceService

OPEN_SESSION = "Masih ada sesi absensi terbuka."
VALID_STATUSES = ("AUTO_VALID", "APPROVED")
# R-33 (keputusan pemilik 2026-10-02): absen pulang hanya untuk absen masuk yang sudah valid.
CHECKOUT_NOT_VALID = ("Absen pulang hanya bisa dilakukan setelah absen masuk valid. "
                      "Absen masuk Anda masih menunggu pemeriksaan.")
ALREADY_TODAY = "Absensi untuk hari ini sudah tercatat (hanya dapat mengajukan ulang jika absensi sebelumnya ditolak)."
# Keputusan pemilik 2026-10-02: ditolak → boleh mengajukan ulang SEKALI; ditolak lagi → hari itu terkunci (tercatat ditolak).
MAX_ATTEMPTS_PER_DAY = 2
ATTEMPTS_USED = ("Absensi hari ini sudah ditolak {n} kali dan tidak dapat diajukan lagi. "
                 "Hari ini tercatat ditolak.")
MAX_GPS_ACCURACY_M = 100  # K-12 (docs/10): akurasi GPS > 100 m ditolak
# Absen web: lokasi browser laptop/PC berasal dari WiFi, bukan GPS — lebih kabur (docs/10 Bagian C).
MAX_WEB_ACCURACY_M = 300
# Lapangan absen di HP, kantor di web (docs/10 Bagian C, 2026-10-01).
CHANNEL_OF_MODE = {"FIELD": "MOBILE", "OFFICE": "WEB"}
WRONG_CHANNEL = {
    "MOBILE": "Anda terdaftar sebagai pekerja kantor — absen lewat web, bukan aplikasi HP.",
    "WEB": "Anda terdaftar sebagai pekerja lapangan — absen lewat aplikasi HP, bukan web.",
}
# R-33: penjelasan wajib saat absen di luar zona dan saat mengajukan ulang absensi yang ditolak.
EXPLANATION_OUTSIDE = "Anda {d:.0f} m dari {site} (radius {r} m). Isi penjelasan mengapa absen di luar zona."
EXPLANATION_RESUBMIT = "Isi penjelasan untuk mengajukan ulang absensi yang ditolak."


class AttendanceSessionService:
    """Layanan inti untuk mengelola rekaman absensi masuk/pulang, validasi koordinat GPS, dan verifikasi sesi kerja."""
    def __init__(self, repo: CRUDAttendanceSession, clock: CRUDOrgClock, faces: FaceService | None = None) -> None:
        self.repo = repo
        self.clock = clock
        self.faces = faces

    async def _employee_for_channel(self, user_id: str, channel: str) -> Any:
        """Karyawan milik akun (employee_id, attendance_mode, unit_id), dengan syarat kanal absen sesuai
        jenis pekerjanya (FIELD → aplikasi HP, OFFICE → web). Jenis pekerja dibaca dari DB, bukan dari klien."""
        row = await self.repo.attendance_mode_of(user_id)
        if row is None:
            raise ValidationError("Akun ini belum tertaut ke data karyawan.")
        # Validasi kontrol channel untuk memastikan tidak ada kecurangan dari karyawan dengan menukar platform (Web vs Mobile).
        # Administrator (pemilik sistem) boleh absen dari web DAN HP, apa pun jenis absen karyawannya (2026-10-06).
        if CHANNEL_OF_MODE.get(row.attendance_mode, "MOBILE") != channel and not row.is_admin:
            raise AppError("WRONG_ATTENDANCE_CHANNEL", WRONG_CHANNEL[channel], status=403)
        return row

    async def check_in(self, org_id: str, user_id: str, *, site_id: UUID, lng: float, lat: float,
                       origin: str, selfie_file_id: UUID | None, accuracy_m: float | None = None,
                       channel: str = "MOBILE", explanation: str | None = None,
                       at: Any = None, work_date: Any = None, face_probe_id: UUID | None = None,
                       online: bool = True, expected_face_sha256: str | None = None) -> Any:
        """
        Mencatat absen masuk harian (check-in) dengan mengevaluasi aturan jarak dan akurasi GPS.
        
        `at`/`work_date`: absen luring (R-34) — jam & tanggal peristiwa yang sudah diverifikasi server
        (jangkar waktu + tanda tangan perangkat), bukan jam terima.

        Pengenalan wajah: `face_probe_id` = gambar wajah sementara (POST /face/probe). Hasil cocok/tidak dihitung
        SERVER setelah absen tercatat; klien tidak lagi dipercaya (aturan inti #3).
        """
        worker = await self._employee_for_channel(user_id, channel)
        employee_id = worker.employee_id
        # K-12: titik GPS yang terlalu kabur tidak bisa membuktikan kehadiran — tolak dengan alasan.
        if channel == "WEB":
            if accuracy_m is not None and accuracy_m > MAX_WEB_ACCURACY_M:
                raise AppError("GPS_INACCURATE",
                               f"Akurasi lokasi browser {accuracy_m:.0f} m terlalu rendah (maksimal "
                               f"{MAX_WEB_ACCURACY_M} m). Nyalakan WiFi perangkat, izinkan akses lokasi, "
                               "lalu coba lagi.", status=422)
        elif accuracy_m is not None and accuracy_m > MAX_GPS_ACCURACY_M:
            raise AppError("GPS_INACCURATE",
                           f"Akurasi GPS {accuracy_m:.0f} m terlalu rendah (maksimal {MAX_GPS_ACCURACY_M} m). "
                           "Pindah ke tempat terbuka, tunggu sinyal GPS menguat, lalu coba lagi.", status=422)
        today = work_date or (await self.clock.local_now(org_id)).today
        # Sesi valid yang lupa ditutup mengunci absen masuk berikutnya (O-10); absen hari lalu yang masih
        # menunggu pemeriksaan tidak mengunci hari baru (R-33).
        if await self.repo.active_on(employee_id, today):
            raise AppError("ALREADY_CHECKED_IN", ALREADY_TODAY, status=409)
        opened = await self.repo.open_session(employee_id)
        if opened is not None and opened.status in VALID_STATUSES:
            raise AppError("OPEN_SESSION", OPEN_SESSION, status=409)
        rejected = await self.repo.rejected_on(employee_id, today)
        if rejected >= MAX_ATTEMPTS_PER_DAY:
            raise AppError("ATTENDANCE_DAY_LOCKED", ATTEMPTS_USED.format(n=rejected), status=409)
        site = await self.repo.site_for_check_in(site_id, org_id, lng, lat)
        if site is None:
            raise NotFoundError("Lokasi")
        # R-33: pekerja lapangan hanya di lokasi proyek unitnya, pekerja kantor hanya di lokasi kantor.
        if worker.attendance_mode == "OFFICE":
            allowed = site.unit_id is None
        else:
            allowed = site.unit_id is not None and site.unit_id == worker.unit_id
        if not allowed:
            raise AppError("SITE_NOT_ALLOWED", "Lokasi ini tidak berlaku untuk Anda. Pilih lokasi kerja Anda.",
                           status=403)
        note = (explanation or "").strip() or None
        if note is None and float(site.distance_m) > site.radius_m:
            raise AppError("EXPLANATION_REQUIRED", EXPLANATION_OUTSIDE.format(
                d=float(site.distance_m), site=site.name, r=site.radius_m), status=422)
        if note is None and rejected >= 1:
            raise AppError("EXPLANATION_REQUIRED", EXPLANATION_RESUBMIT, status=422)
        try:
            row = await self.repo.insert(
                org_id=org_id, employee_id=employee_id, work_date=today, site_id=site_id, site_label=site.name,
                lng=lng, lat=lat, origin=origin, selfie_file_id=selfie_file_id,
                face_result=None, face_similarity=None, source=channel, explanation=note,
                at=at,
            )
            return await self.apply_face(org_id, user_id, row, "CHECK_IN", face_probe_id, online=online,
                                         expected_sha256=expected_face_sha256, device=channel)
        except IntegrityError as exc:
            # Aturan dari trigger (mis. di luar radius tanpa swafoto) → 422 dengan pesannya.
            rule = trigger_rule_message(exc)
            if rule:
                raise ValidationError(rule) from None
            if "attendance_active_uidx" in str(exc) or "employee_id_work_date" in str(exc):
                raise AppError("ALREADY_CHECKED_IN", ALREADY_TODAY, status=409) from None
            raise

    async def apply_face(self, org_id: str, user_id: str, row: Any, event: str, face_probe_id: UUID | None, *,
                         online: bool = True, expected_sha256: str | None = None, device: str | None = None) -> Any:
        """
        Mencocokkan wajah untuk absen `row` (masuk/pulang) dan menyimpan hasilnya. Hasil bermasalah menaikkan absensi
        ke antrean periksa; tidak pernah menolak. Tanpa `face_probe_id`: karyawan tanpa pendaftaran wajah tidak
        terpengaruh; pekerja lapangan yang SUDAH mendaftar tetapi absen tanpa data wajah (APK lama, kamera ditolak,
        luring tanpa blok wajah) ditandai Perlu review dengan catatan — wajah tidak boleh dilewati diam-diam.
        """
        if self.faces is None:
            return row
        if face_probe_id is None:
            if await self.faces.face_expected(user_id):
                return await self.repo.flag_missing_face(
                    row.id, event, "wajah tidak diperiksa: karyawan sudah mendaftar wajah tetapi absen tanpa data wajah")
            return row
        outcome: FaceOutcome = await self.faces.verify_for_attendance(
            org_id, user_id, probe_id=face_probe_id, event=event, attendance_id=row.id, device=device,
            online=online, expected_sha256=expected_sha256)
        return await self.repo.set_face(row.id, event, check_id=outcome.check_id, result=outcome.result,
                                        similarity=outcome.similarity, flag_review=outcome.flag_review)

    async def reverify_faces(self, limit: int = 50) -> tuple[int, int]:
        """Penjadwal: hitung & cocokkan ulang wajah yang tertunda (face-service mati saat absen). → (selesai, tersisa)."""
        if self.faces is None:
            return 0, 0
        done, left = await self.faces.recompute_pending(limit)
        for attendance_id, event, outcome in done:
            await self.repo.set_face(attendance_id, event, check_id=outcome.check_id, result=outcome.result,
                                     similarity=outcome.similarity, flag_review=outcome.flag_review)
        return len(done), left

    async def purge_faces(self) -> int:
        """Penjadwal: hapus gambar wajah yang lewat masa simpan."""
        return await self.faces.purge_expired() if self.faces is not None else 0

    async def check_out(self, user_id: str, channel: str = "MOBILE", *, org_id: str | None = None,
                        face_probe_id: UUID | None = None, online: bool = True,
                        expected_face_sha256: str | None = None) -> Any:
        """
        Menutup sesi absensi harian yang sedang terbuka (absen pulang).
        
        Menutup sesi terbuka milik sendiri — tanggal berapa pun, agar sesi yang lupa ditutup tidak
        mengunci check-in berikutnya. Status tidak diubah; pulang cepat diputuskan trigger.
        R-33: hanya sesi yang sudah valid (Valid otomatis / Disetujui) yang boleh absen pulang.
        """
        worker = await self._employee_for_channel(user_id, channel)
        session = await self.repo.open_session(worker.employee_id, valid_only=True)
        if session is None:
            # Memastikan tidak bisa absen pulang jika absen masuknya ditolak atau masih dalam proses peninjauan.
            if await self.repo.open_session(worker.employee_id) is not None:
                raise AppError("CHECKOUT_NOT_VALID", CHECKOUT_NOT_VALID, status=409)
            raise AppError("NO_OPEN_SESSION", "Tidak ada sesi absensi terbuka.", status=409)
        row = await self.repo.close(session.id)
        if org_id is not None:
            row = await self.apply_face(org_id, user_id, row, "CHECK_OUT", face_probe_id, online=online,
                                        expected_sha256=expected_face_sha256, device=channel)
        return row

    async def list_attendance(self, org_id: str, user_id: str, *, view_all: bool, employee_id: UUID | None,
                              date_from: Any, date_to: Any, status: str | None,
                              page: int, size: int, scope: str = "all") -> tuple[list[Any], int]:
        """
        Mendapatkan daftar absensi berdasarkan filter, disesuaikan dengan hak visibilitas pengguna.
        
        R-33: Finance & OPS (`view:all_attendance`) melihat semua; PM melihat miliknya + bawahan lapangan
        di unitnya; selain itu hanya milik sendiri. Di luar cakupan → tidak tampil (tidak dibocorkan).
        Setiap baris membawa `can_review` dari server.
        """
        return await self.repo.list_page(org_id, user_id, view_all=view_all, employee_id=employee_id,
                                         date_from=date_from, date_to=date_to, status=status, scope=scope,
                                         limit=size, offset=(page - 1) * size)

    async def today(self, org_id: str) -> Any:
        """Tanggal kerja hari ini menurut zona waktu organisasi — sama dengan `work_date` absen masuk."""
        return (await self.clock.local_now(org_id)).today

    async def explain_attendance(self, org_id: str, user_id: str, attendance_id: UUID, explanation: str) -> None:
        """
        Memberikan penjelasan tambahan untuk sesi absensi yang memerlukan peninjauan.
        """
        attendance = await self.repo.get(attendance_id, org_id)
        employee_id = await self.repo.employee_of(user_id)
        # Memastikan karyawan hanya dapat memberikan alasan pada absensi miliknya sendiri (V-09).
        if attendance is None or attendance.employee_id != employee_id:
            raise NotFoundError("Absensi")  # milik orang lain tidak dibocorkan (V-09)
        if attendance.status != "NEEDS_REVIEW":
            raise AppError("INVALID_STATE",
                           "Hanya absensi sendiri yang menunggu pemeriksaan dapat diberi penjelasan.", status=409)
        if not explanation.strip():
            raise ValidationError("Penjelasan wajib diisi.")
        await self.repo.set_explanation(attendance_id, explanation.strip())

    async def review_attendance(self, org_id: str, user_id: str, attendance_id: UUID,
                                approve: bool, note: str | None) -> str:
        """
        Meninjau (menyetujui atau menolak) sesi absensi yang anomali.
        
        R-33: PM → bawahan lapangan di unitnya; Finance → pekerja kantor selain Finance; OPS → Finance.
        Tidak ada yang meninjau absensinya sendiri (cakupan: CRUD `CAN_REVIEW`).
        """
        attendance = await self.repo.get(attendance_id, org_id)
        if attendance is None:
            raise NotFoundError("Absensi")
        reviewer = await self.repo.employee_of(user_id)
        # Aturan empat mata: peninjau tidak boleh menyetujui/menolak absensinya sendiri.
        if attendance.employee_id == reviewer:
            raise ForbiddenError("Anda tidak boleh memverifikasi absensi sendiri.")
        if not await self.repo.can_review(user_id, attendance.employee_id):
            raise ForbiddenError("Absensi ini berada di luar kewenangan peninjauan Anda.")
        if attendance.status != "NEEDS_REVIEW":
            raise AppError("INVALID_STATE", "Absensi tidak menunggu pemeriksaan.", status=409)
        if not (note or "").strip():
            raise ValidationError("Catatan pemeriksaan wajib diisi.")
            
        status = "APPROVED" if approve else "REJECTED"
        await self.repo.set_review(attendance_id, status, reviewer, (note or "").strip())
        return status
