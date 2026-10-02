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
from app.core.security import CurrentUser
from app.crud.crud_attendance_session import CRUDAttendanceSession
from app.crud.crud_monitoring import CRUDMonitoring
from app.crud.crud_org_clock import CRUDOrgClock
from app.crud.crud_plan_access import CRUDPlanAccess
from app.services.attendance_session_service import SEE_ALL

HIDDEN = (PlanStatus.CANCELLED, PlanStatus.COMPLETED)   # operations.js timeline()
REPORTED = ("APPROVED", "SUBMITTED", "CHANGES_REQUESTED")


def _day_state(work_date: date, report_status: str | None, today: date) -> str:
    """operations.js dayState."""
    if report_status in REPORTED:
        return str(report_status)
    if work_date < today:
        return "LATE"
    return "TODAY" if work_date == today else "UPCOMING"


def _month_range(month: str | None, today: date) -> tuple[str, date, date]:
    try:
        first = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        raise ValidationError("Bulan harus berformat YYYY-MM.") from None
    following = first.replace(year=first.year + 1, month=1) if first.month == 12 else first.replace(month=first.month + 1)
    return first.strftime("%Y-%m"), first, following


class MonitoringService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDMonitoring(db)

    async def _today(self, org_id: str) -> date:
        today: date = (await CRUDOrgClock(self.db).local_now(org_id)).today
        return today

    async def timeline(self, user: CurrentUser, date_from: date | None, date_to: date | None) -> list[dict[str, Any]]:
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
        label, starts, ends = _month_range(month, await self._today(user.organization_id))
        scope: str | None = None
        if not set(user.roles) & SEE_ALL:
            own = await CRUDAttendanceSession(self.db).employee_of(user.user_id)
            if own is None:
                return {"month": label, "employees": []}
            scope = str(own)
        rows = await self.repo.attendance_recap(user.organization_id, starts, ends, scope)
        return {"month": label, "employees": [dict(row._mapping) for row in rows]}
