"""
app/services/monitoring_service.py
Pemantauan OPS (V-30, dok 03 M11) — lini masa dikelompokkan per pekerjaan (prototipe operations.js
timeline()) dan rekap absensi per karyawan. Visibilitas SK memakai aturan `GET /work-plans` (V-07);
siapa yang melihat absensi seluruh organisasi memakai aturan `GET /attendance`.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import ValidationError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.crud.crud_monitoring import CRUDMonitoring
from app.crud.crud_org_clock import CRUDOrgClock
from app.crud.crud_plan_access import CRUDPlanAccess

HIDDEN = (PlanStatus.CANCELLED, PlanStatus.COMPLETED)   # operations.js timeline()
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
    following = first.replace(year=first.year + 1, month=1) if first.month == 12 else first.replace(month=first.month + 1)
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

    async def timeline(self, user: CurrentUser, date_from: date | None, date_to: date | None) -> list[dict[str, Any]]:
        """
        Membangun lini masa (timeline) dari seluruh SK yang visibel bagi pengguna.
        
        Mencakup jadwal harian dan status tiap hari, dengan menyaring SK yang dibatalkan
        atau sudah selesai sesuai filter periode.
        
        Args:
            user: Informasi pengguna yang sedang mengakses.
            date_from: Filter tanggal mulai (opsional).
            date_to: Filter tanggal selesai (opsional).
            
        Returns:
            list[dict[str, Any]]: Daftar pekerjaan (SK) dengan data jadwal hariannya.
        """
        # Ambil SK yang boleh dilihat pengguna sesuai hak aksesnya (V-07)
        plans = [
            p for p in await CRUDPlanAccess(self.db).visible_plans(user.organization_id, user.user_id, None)
            if p.status not in HIDDEN
            and (date_from is None or p.period_end >= date_from)
            and (date_to is None or p.period_start <= date_to)
        ]
        plans.sort(key=lambda p: (p.period_start, p.title))
        ids = [str(p.id) for p in plans]
        days: dict[str, list[Any]] = {plan_id: [] for plan_id in ids}
        for day in await self.repo.plan_days(ids):
            days[day.work_plan_id].append(day)
        leaders = await self.repo.names([str(p.leader_employee_id) for p in plans if p.leader_employee_id])
        today = await self._today(user.organization_id)

        groups = []
        for plan in plans:
            rows = [{"id": str(d.id), "work_date": d.work_date, "title": d.title,
                     "state": _day_state(d.work_date, d.report_status, today)} for d in days[str(plan.id)]]
            leader = str(plan.leader_employee_id) if plan.leader_employee_id else None
            groups.append({
                "id": str(plan.id), "number": plan.number, "title": plan.title, "status": plan.status,
                "unit_id": plan.unit_id, "location_text": plan.location_text,
                "period_start": plan.period_start, "period_end": plan.period_end,
                "leader": {"employee_id": leader, "full_name": leaders.get(leader or "")} if leader else None,
                "total_days": len(rows),
                "approved_days": sum(1 for r in rows if r["state"] == "APPROVED"),
                "late_days": sum(1 for r in rows if r["state"] == "LATE"),
                "days": rows,
            })
        return groups

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
        return {"month": label, "employees": [dict(row._mapping) for row in rows],
                "records": [dict(row._mapping) for row in days]}
