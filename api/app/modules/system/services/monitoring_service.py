"""
app/modules/system/services/monitoring_service.py
Pemantauan OPS (V-30, dok 03 M11) — lini masa dikelompokkan per pekerjaan (prototipe operations.js
timeline()) dan rekap absensi per karyawan. Visibilitas SK memakai aturan `GET /work-plans` (V-07);
siapa yang melihat absensi seluruh organisasi memakai aturan `GET /attendance`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.system.repositories.monitoring_repository import CRUDMonitoring
from app.shared.org_clock import CRUDOrgClock

REPORTED = ("APPROVED", "SUBMITTED", "CHANGES_REQUESTED")


def _day_state(work_date: date, report_status: str | None, today: date) -> str:
    """
    Menentukan status hari (day state) berdasarkan tanggal eksekusi dan pelaporan.

    Status ini meniru logika prototipe `operations.js dayState()`.

    Args:
        work_date: Tanggal pelaksanaan jadwal.
        report_status: Status laporan di sistem jika ada.
        today: Tanggal acuan saat ini.

    Returns:
        str: String status (misal: "LATE", "TODAY", "UPCOMING", dll).
    """
    if report_status in REPORTED:
        return str(report_status)
    if work_date < today:
        return "LATE"
    return "TODAY" if work_date == today else "UPCOMING"


def _month_range(month: str | None, today: date) -> tuple[str, date, date]:
    """
    Menghasilkan rentang tanggal untuk sebulan penuh.

    Args:
        month: String bulan berformat 'YYYY-MM'. Jika None, gunakan bulan ini.
        today: Tanggal acuan hari ini.

    Returns:
        tuple[str, date, date]: Berisi label bulan (YYYY-MM), tanggal awal bulan, dan tanggal awal bulan berikutnya.

    Raises:
        ValidationError: Jika format bulan tidak sesuai.
    """
    try:
        first = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        raise ValidationError("Bulan harus berformat YYYY-MM.") from None
    following = (
        first.replace(year=first.year + 1, month=1) if first.month == 12 else first.replace(month=first.month + 1)
    )
    return first.strftime("%Y-%m"), first, following


class MonitoringService:
    """Layanan untuk fungsi pemantauan operasi (OPS) seperti lini masa SK dan rekap absensi."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDMonitoring(db)

    async def _today(self, org_id: str) -> date:
        """
        Mengambil tanggal hari ini berdasarkan zona waktu organisasi.

        Args:
            org_id: ID organisasi.

        Returns:
            date: Objek tanggal hari ini.
        """
        today: date = (await CRUDOrgClock(self.db).local_now(org_id)).today
        return today

    async def attendance_recap(self, user: CurrentUser, month: str | None) -> dict[str, Any]:
        """
        Menyusun rekap absensi karyawan dalam waktu sebulan.

        Args:
            user: Informasi pengguna saat ini.
            month: String bulan ('YYYY-MM') atau None untuk bulan berjalan.

        Returns:
            dict[str, Any]: Data rekapitulasi daftar karyawan beserta catatan absensinya.
        """
        label, starts, ends = _month_range(month, await self._today(user.organization_id))
        # Logika aksesibilitas rekap absensi berdasarkan peran pengguna:
        # R-33: Finance & OPS semua; PM hanya bawahan lapangan di unitnya; selain itu milik sendiri.
        if Permission.VIEW_ALL_ATTENDANCE.value in user.permissions:
            scope = "all"
        elif "PM" in user.roles:
            scope = "subordinates"
        else:
            scope = "own"
        rows = await self.repo.attendance_recap(user.organization_id, starts, ends, user.user_id, scope)
        days = await self.repo.attendance_recap_days(user.organization_id, starts, ends, user.user_id, scope)
        return {
            "month": label,
            "employees": [dict(row._mapping) for row in rows],
            "records": [dict(row._mapping) for row in days],
        }
