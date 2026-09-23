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
from app.core.time import jakarta_now
from app.repositories.attendance_monitor_repo import AttendanceMonitorRepo

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
    def __init__(self, repo: AttendanceMonitorRepo) -> None:
        self.repo = repo

    async def check_missing_check_ins(self, org_id: UUID | str) -> MissingCheckInResult:
        now = jakarta_now()
        today = now.date()
        # Hari kerja Senin–Jumat mulai 09.00 WIB (K-11: jam kerja 08.00–17.00).
        if now.weekday() >= 5 or now.time() < CHECK_IN_DEADLINE:
            return MissingCheckInResult(alerted=False, check_ins_today=0)

        count = await self.repo.check_in_count(org_id, today)
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
        today = jakarta_now().date()
        count = await self.repo.needs_review_count(org_id, today)
        average = await self.repo.needs_review_daily_average(org_id, today, REVIEW_WINDOW_DAYS)

        alerted = count >= REVIEW_SPIKE_MINIMUM and count > REVIEW_SPIKE_FACTOR * average
        if alerted:
            await send_business_alert(
                "Janggal — absensi perlu review",
                f"{count} absensi NEEDS_REVIEW hari ini; rata-rata {REVIEW_WINDOW_DAYS} hari terakhir "
                f"{average:.1f}/hari. Periksa ambang wajah, koordinat lokasi, atau akurasi GPS.",
            )
        return NeedsReviewResult(alerted=alerted, needs_review_today=count, daily_average=round(average, 2))
