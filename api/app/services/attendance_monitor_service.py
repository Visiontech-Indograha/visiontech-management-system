"""
app/services/attendance_monitor_service.py
Aturan peringatan bisnis absensi (dok 17 §5.3, P4-9). Pesan hanya berisi angka & waktu (dok 17 §2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.alerts import send_business_alert
from app.core.config import settings
from app.core.time import jakarta_now
from app.crud.crud_attendance_monitor import CRUDAttendanceMonitor
from app.crud.crud_attendance_session import CRUDAttendanceSession
from app.services.notification_service import NotificationService

WIB = ZoneInfo("Asia/Jakarta")
CHECK_IN_DEADLINE = time(9, 0)
REVIEW_WINDOW_DAYS = 14
REVIEW_SPIKE_FACTOR = 2.0
REVIEW_SPIKE_MINIMUM = 3  # di bawah ini bukan lonjakan, meski rata-rata 0


@dataclass(frozen=True)
class MissingCheckInResult:
    alerted: bool
    check_ins_today: int


@dataclass(frozen=True)
class NeedsReviewResult:
    alerted: bool
    needs_review_today: int
    daily_average: float


class AttendanceMonitorService:
    """Layanan untuk memantau dan menghasilkan notifikasi terkait kedisiplinan dan janggalan absensi harian."""
    def __init__(self, repo: CRUDAttendanceMonitor) -> None:
        self.repo = repo

    async def check_missing_check_ins(self, org_id: UUID | str) -> MissingCheckInResult:
        """
        Memeriksa apakah tidak ada yang absen masuk hingga tenggat waktu yang ditentukan, lalu mengirimkan peringatan jika diperlukan.

        Args:
            org_id: ID organisasi.

        Returns:
            Hasil pemeriksaan berupa boolean peringatan terkirim dan jumlah check-in hari ini.
        """
        now = jakarta_now()
        today = now.date()
        # Hari kerja Senin–Jumat mulai 09.00 WIB (K-11: jam kerja 08.00–17.00).
        # Logika pembatasan waktu bisnis: Jangan periksa pada akhir pekan atau sebelum batas toleransi check-in.
        if now.weekday() >= 5 or now.time() < CHECK_IN_DEADLINE:
            return MissingCheckInResult(alerted=False, check_ins_today=0)

        count = await self.repo.check_in_count(org_id, today)
        # Jika ada yang absen masuk, atau tidak ada karyawan aktif yang perlu diabsen, maka abaikan.
        if count or not await self.repo.active_employee_count(org_id):
            return MissingCheckInResult(alerted=False, check_ins_today=count)

        last = await self.repo.last_check_in_at(org_id)
        last_text = last.astimezone(WIB).strftime("%d-%m-%Y %H.%M WIB") if last else "belum pernah"
        await send_business_alert(
            "Janggal — absensi",
            f"Belum ada absensi masuk sampai {now.strftime('%H.%M')} WIB.\nTerakhir tercatat: {last_text}.",
        )
        return MissingCheckInResult(alerted=True, check_ins_today=0)

    async def check_needs_review_spike(self, org_id: UUID | str) -> NeedsReviewResult:
        """
        Memantau lonjakan abnormal pada status absensi "Perlu Review" untuk mengidentifikasi potensi gangguan lokasi/GPS.

        Args:
            org_id: ID organisasi.

        Returns:
            Hasil evaluasi lonjakan.
        """
        today = jakarta_now().date()
        count = await self.repo.needs_review_count(org_id, today)
        average = await self.repo.needs_review_daily_average(org_id, today, REVIEW_WINDOW_DAYS)

        # Memicu peringatan jika jumlah yang butuh ditinjau secara abnormal lebih tinggi dari hari-hari biasa.
        alerted = count >= REVIEW_SPIKE_MINIMUM and count > REVIEW_SPIKE_FACTOR * average
        if alerted:
            await send_business_alert(
                "Janggal — absensi perlu review",
                f"{count} absensi NEEDS_REVIEW hari ini; rata-rata {REVIEW_WINDOW_DAYS} hari terakhir "
                f"{average:.1f}/hari. Periksa ambang wajah, koordinat lokasi, atau akurasi GPS.",
            )
        return NeedsReviewResult(alerted=alerted, needs_review_today=count, daily_average=round(average, 2))

    async def auto_checkout_unclosed_sessions(self, org_id: UUID | str) -> int:
        """
        Menutup otomatis sesi absensi yang belum check-out pada pukul 19:00 WIB
        dengan keterangan 'Lupa absen pulang (ditutup otomatis oleh sistem pada pukul 19:00)'.
        """
        now = jakarta_now()
        close_hour, close_min = [int(p) for p in settings.ATTENDANCE_CLOSE_TIME.split(":")]
        if not settings.SKIP_ATTENDANCE_HOURS_CHECK and now.time() < time(close_hour, close_min):
            return 0

        today = now.date()
        close_time = now.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)
        explanation = f"Lupa absen pulang (ditutup otomatis oleh sistem pada pukul {settings.ATTENDANCE_CLOSE_TIME})"

        session_repo = CRUDAttendanceSession(self.repo.db)
        closed_rows = await session_repo.auto_checkout_unclosed(org_id, today, close_time, explanation)
        if closed_rows:
            emp_ids = [str(r.employee_id) for r in closed_rows]
            await NotificationService(self.repo.db).attendance_auto_checkout_bulk(str(org_id), emp_ids)
        return len(closed_rows)
