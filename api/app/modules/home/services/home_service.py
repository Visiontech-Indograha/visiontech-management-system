"""
app/modules/home/services/home_service.py

Menghitung ringkasan Beranda dengan memakai service modul lain (tanpa SQL sendiri), sehingga lingkup
data per peran sama persis dengan daftar di masing-masing modul.
"""

from __future__ import annotations

from typing import Any

from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.assets.services.asset_service import AssetService
from app.modules.attendance.services.attendance_session_service import AttendanceSessionService
from app.modules.home.schemas.home_schema import HomeSummary
from app.modules.leaves.services.leave_service import LeaveService
from app.modules.mess.services.mess_service import MessService
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.offboarding.services.offboarding_service import OffboardingService
from app.modules.overtime.services.overtime_service import OvertimeService
from app.modules.work_plans.services.daily_correction_service import DailyCorrectionService

# Status cuti yang menunggu keputusan, menurut peran peninjau (PM memutus PENDING; HR/admin juga APPROVED_BY_PM).
_LEAVE_REVIEWERS = {
    "SUPER_ADMIN": ("PENDING", "APPROVED_BY_PM"),
    "ADMIN_HR_GA": ("PENDING", "APPROVED_BY_PM"),
    "PROJECT_MANAGER": ("PENDING",),
}
_CORRECTION_REVIEWERS = ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER", "ADMIN_HR_GA")


class HomeService:
    def __init__(
        self,
        leaves: LeaveService,
        attendance: AttendanceSessionService,
        overtime: OvertimeService,
        mess: MessService,
        assets: AssetService,
        corrections: DailyCorrectionService,
        offboarding: OffboardingService,
        notifications: NotificationService,
    ) -> None:
        self.leaves = leaves
        self.attendance = attendance
        self.overtime = overtime
        self.mess = mess
        self.assets = assets
        self.corrections = corrections
        self.offboarding = offboarding
        self.notifications = notifications

    async def summary(self, user: CurrentUser) -> HomeSummary:
        perms = set(user.permissions)
        out = HomeSummary()

        own = str(user.employee_id) if user.employee_id else None
        leaves: list[Any] = list(await self.leaves.list(user))
        out.my_leaves_pending = sum(
            1 for r in leaves if str(r.employee_id) == own and r.status in ("PENDING", "APPROVED_BY_PM")
        )
        wanted = _LEAVE_REVIEWERS.get(user.role, ())
        out.leaves_to_review = sum(1 for r in leaves if r.status in wanted and str(r.employee_id) != own)

        if Permission.REVIEW_ATTENDANCE.value in perms:
            _, total = await self.attendance.list_attendance(
                user.organization_id,
                user.user_id,
                view_all=Permission.VIEW_ALL_ATTENDANCE.value in perms,
                employee_id=None,
                date_from=None,
                date_to=None,
                status="NEEDS_REVIEW",
                page=1,
                size=1,
            )
            out.attendance_to_review = total

        if Permission.REVIEW_OVERTIME.value in perms:
            rows = await self.overtime.list_overtimes(user)
            out.overtime_to_review = sum(1 for r in rows if r.status == "PENDING_PM")

        if Permission.REVIEW_MESS.value in perms:
            out.mess_to_review = len(await self.mess.list_stays(None, None, None, "REQUESTED"))

        if Permission.MANAGE_ASSETS.value in perms:
            out.loan_requests_to_review = len(await self.assets.requests(user, status="PENDING"))

        if user.role in _CORRECTION_REVIEWERS:
            inbox = await self.corrections.inbox(user, None)
            out.corrections_to_review = sum(1 for r in inbox if r.status in ("REQUESTED", "IN_REVIEW"))

        if Permission.MANAGE_OFFBOARDING.value in perms:
            rows = await self.offboarding.list_all(user, None)
            out.offboarding_open = sum(1 for r in rows if r.status != "COMPLETED")

        out.notifications_unread = await self.notifications.unread_count(user.user_id)
        out.total_to_review = (
            out.leaves_to_review
            + out.attendance_to_review
            + out.overtime_to_review
            + out.mess_to_review
            + out.loan_requests_to_review
            + out.corrections_to_review
            + out.offboarding_open
        )
        return out
