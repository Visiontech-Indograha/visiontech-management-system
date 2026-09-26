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
from app.repositories.attendance_session_repo import AttendanceSessionRepo
from app.repositories.org_clock_repo import OrgClockRepo

OPEN_SESSION = "Masih ada sesi absensi terbuka."
SEE_ALL = {"FINANCE", "HR", "OPS", "ADMIN"}  # prototipe operations.js attendance(): canAll (+ ADMIN)
ALREADY_TODAY = "Absensi untuk hari ini sudah tercatat (hanya dapat mengajukan ulang jika absensi sebelumnya ditolak)."
MAX_GPS_ACCURACY_M = 100  # K-12 (docs/10): akurasi GPS > 100 m ditolak


class AttendanceSessionService:
    def __init__(self, repo: AttendanceSessionRepo, clock: OrgClockRepo) -> None:
        self.repo = repo
        self.clock = clock

    async def _employee(self, user_id: str) -> Any:
        employee_id = await self.repo.employee_of(user_id)
        if employee_id is None:
            raise ValidationError("Akun ini belum tertaut ke data karyawan.")
        return employee_id

    async def check_in(self, org_id: str, user_id: str, *, site_id: UUID, lng: float, lat: float,
                       origin: str, selfie_file_id: UUID | None, face_result: str | None,
                       face_similarity: float | None, accuracy_m: float | None = None) -> Any:
        # K-12: titik GPS yang terlalu kabur tidak bisa membuktikan kehadiran — tolak dengan alasan.
        if accuracy_m is not None and accuracy_m > MAX_GPS_ACCURACY_M:
            raise AppError("GPS_INACCURATE",
                           f"Akurasi GPS {accuracy_m:.0f} m terlalu rendah (maksimal {MAX_GPS_ACCURACY_M} m). "
                           "Pindah ke tempat terbuka, tunggu sinyal GPS menguat, lalu coba lagi.", status=422)
        employee_id = await self._employee(user_id)
        if await self.repo.open_session(employee_id) is not None:
            raise AppError("OPEN_SESSION", OPEN_SESSION, status=409)
        today = (await self.clock.local_now(org_id)).today
        if await self.repo.active_on(employee_id, today):
            raise AppError("ALREADY_CHECKED_IN", ALREADY_TODAY, status=409)
        label = await self.repo.site_label(site_id, org_id)
        if label is None:
            raise NotFoundError("Lokasi")
        try:
            return await self.repo.insert(
                org_id=org_id, employee_id=employee_id, work_date=today, site_id=site_id, site_label=label,
                lng=lng, lat=lat, origin=origin, selfie_file_id=selfie_file_id,
                face_result=face_result, face_similarity=face_similarity,
            )
        except IntegrityError as exc:
            # Aturan dari trigger (mis. di luar radius tanpa swafoto) → 422 dengan pesannya.
            rule = trigger_rule_message(exc)
            if rule:
                raise ValidationError(rule) from None
            if "attendance_active_uidx" in str(exc) or "employee_id_work_date" in str(exc):
                raise AppError("ALREADY_CHECKED_IN", ALREADY_TODAY, status=409) from None
            raise

    async def check_out(self, user_id: str) -> Any:
        """Menutup sesi terbuka milik sendiri — tanggal berapa pun, agar sesi yang lupa ditutup tidak
        mengunci check-in berikutnya. Status tidak diubah; pulang cepat diputuskan trigger."""
        employee_id = await self._employee(user_id)
        session = await self.repo.open_session(employee_id)
        if session is None:
            raise AppError("NO_OPEN_SESSION", "Tidak ada sesi absensi terbuka.", status=409)
        return await self.repo.close(session.id)

    async def list_attendance(self, org_id: str, user_id: str, roles: list[str], *, employee_id: UUID | None,
                              date_from: Any, date_to: Any, status: str | None,
                              page: int, size: int) -> tuple[list[Any], int]:
        """Prototipe (operations.js): FINANCE, HR, OPS — dan ADMIN — melihat seluruh organisasi;
        PM: miliknya dan karyawan di unit yang dipegangnya (R-10);
        selain itu hanya absensi sendiri (filter karyawan lain → daftar kosong, tidak dibocorkan)."""
        scope: Any = employee_id
        if not set(roles) & SEE_ALL and "PM" in roles:
            return await self.repo.list_page(org_id, employee_id=employee_id, date_from=date_from, date_to=date_to,
                                             status=status, limit=size, offset=(page - 1) * size,
                                             pm_user_id=user_id)
        if not set(roles) & SEE_ALL:
            own = await self.repo.employee_of(user_id)
            if own is None or (employee_id is not None and str(employee_id) != str(own)):
                return [], 0
            scope = own
        return await self.repo.list_page(org_id, employee_id=scope, date_from=date_from, date_to=date_to,
                                         status=status, limit=size, offset=(page - 1) * size)

    async def explain_attendance(self, org_id: str, user_id: str, attendance_id: UUID, explanation: str) -> None:
        attendance = await self.repo.get(attendance_id, org_id)
        employee_id = await self.repo.employee_of(user_id)
        if attendance is None or attendance.employee_id != employee_id:
            raise NotFoundError("Absensi")  # milik orang lain tidak dibocorkan (V-09)
        if attendance.status != "NEEDS_REVIEW":
            raise AppError("INVALID_STATE",
                           "Hanya absensi sendiri yang menunggu pemeriksaan dapat diberi penjelasan.", status=409)
        if not explanation.strip():
            raise ValidationError("Penjelasan wajib diisi.")
        await self.repo.set_explanation(attendance_id, explanation.strip())

    async def review_attendance(self, org_id: str, user_id: str, attendance_id: UUID,
                                approve: bool, note: str | None, *, review_all: bool) -> str:
        """Finance/Admin (review:attendance) seluruh organisasi; PM hanya karyawan di unitnya,
        OPS lintas unit (revisi pemilik R-10)."""
        attendance = await self.repo.get(attendance_id, org_id)
        if attendance is None:
            raise NotFoundError("Absensi")
        if not review_all and not await self.repo.manages_employee(user_id, attendance.employee_id):
            raise ForbiddenError("Absensi ini berada di luar unit atau kewenangan Anda.")
        if attendance.status != "NEEDS_REVIEW":
            raise AppError("INVALID_STATE", "Absensi tidak menunggu pemeriksaan.", status=409)
        reviewer = await self.repo.employee_of(user_id)
        if attendance.employee_id == reviewer:
            raise ForbiddenError("Anda tidak boleh memverifikasi absensi sendiri.")
        if not (note or "").strip():
            raise ValidationError("Catatan pemeriksaan wajib diisi.")
        status = "APPROVED" if approve else "REJECTED"
        await self.repo.set_review(attendance_id, status, reviewer, (note or "").strip())
        return status
