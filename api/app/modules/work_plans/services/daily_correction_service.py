"""
app/modules/work_plans/services/daily_correction_service.py
Koreksi laporan harian (keputusan pemilik 2026-10-27): jadwal COMPLETED yang laporannya perlu diperbaiki.

  REQUESTED --(PM setujui)--> REVISING --(ketua kirim revisi)--> IN_REVIEW --(PM terima)--> ACCEPTED
     |                           ^                                    |
     +--(PM tolak)--> REJECTED   +-------------(PM kembalikan)--------+

- Hanya ketua tim jadwal itu yang mengajukan & mengirim revisi; hanya PM/OM divisi (atau SUPER_ADMIN) yang memutuskan.
- Saat REVISING / IN_REVIEW jadwal dibuka kembali (ONGOING) agar progres item & laporan bisa diperbaiki; saat
  diterima jadwal kembali COMPLETED. Satu koreksi terbuka per jadwal.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.security import CurrentUser
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.work_plans.repositories.daily_correction_repository import DailyCorrectionRepository
from app.modules.work_plans.repositories.plan_item_repository import PlanItemRepository
from app.modules.work_plans.schemas.daily_correction_schema import CorrectionCreate, CorrectionDecide
from app.shared.access.access_service import DailyNeed, check_daily_access, is_admin, require_daily_status

OPEN = ("REQUESTED", "REVISING", "IN_REVIEW")


class DailyCorrectionService:
    """Use case koreksi laporan harian."""

    def __init__(self, db: AsyncSession, repo: DailyCorrectionRepository | None = None) -> None:
        self.db = db
        self.repo = repo if repo is not None else DailyCorrectionRepository(db)

    async def request(self, user: CurrentUser, daily_plan_id: UUID, data: CorrectionCreate) -> Any:
        access = await check_daily_access(self.db, daily_plan_id, user, DailyNeed.LEADER)
        require_daily_status(access, "COMPLETED")
        if user.employee_id is None:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        if any(c.status in OPEN for c in await self.repo.of_plan(daily_plan_id)):
            raise AppError("CORRECTION_OPEN", "Sudah ada koreksi yang sedang berjalan untuk jadwal ini.", status=409)
        correction_id = await self.repo.insert(daily_plan_id, user.employee_id, data.reason.strip())
        notifier = NotificationService(self.db)
        await notifier.notify_division_managers(
            user.employee_id, "CORRECTION_REQUESTED",
            f"{await notifier.employee_name(user.employee_id)} meminta koreksi laporan harian",
            data.reason.strip(), target="correction", roles=("PROJECT_MANAGER",),
        )
        return await self.repo.get(correction_id)

    async def of_plan(self, user: CurrentUser, daily_plan_id: UUID) -> list[Any]:
        await check_daily_access(self.db, daily_plan_id, user, DailyNeed.VIEW)
        return await self.repo.of_plan(daily_plan_id)

    async def inbox(self, user: CurrentUser, status: str | None) -> list[Any]:
        everything = is_admin(user) or user.has_role("ADMIN_HR_GA")
        return await self.repo.inbox(user.employee_id, status, all_divisions=everything)

    async def _locked(self, correction_id: UUID) -> Any:
        row = await self.repo.for_update(correction_id)
        if row is None:
            raise NotFoundError("Koreksi laporan")
        return row

    async def decide(self, user: CurrentUser, correction_id: UUID, data: CorrectionDecide) -> Any:
        row = await self._locked(correction_id)
        await check_daily_access(self.db, row.daily_plan_id, user, DailyNeed.MANAGE)
        note = data.note.strip() if data.note else None
        reviewer = user.employee_id
        if data.decision in ("APPROVE", "REJECT"):
            if row.status != "REQUESTED":
                raise AppError("INVALID_STATE", "Permintaan koreksi ini sudah diputuskan.", status=409)
            if data.decision == "APPROVE":
                await self.repo.set_status(correction_id, "REVISING", reviewer=reviewer, note=note)
                await self.repo.set_plan_status(row.daily_plan_id, "ONGOING")
            else:
                await self.repo.set_status(correction_id, "REJECTED", reviewer=reviewer, note=note)
        else:
            if row.status != "IN_REVIEW":
                raise AppError("INVALID_STATE", "Belum ada revisi yang menunggu pemeriksaan.", status=409)
            if data.decision == "ACCEPT":
                if not data.force:
                    gaps = await PlanItemRepository(self.db).done_items_photo_gaps(row.daily_plan_id)
                    if gaps:
                        detail = "; ".join(f"{title}: {', '.join(missing)}" for title, missing in gaps)
                        raise AppError(
                            "PHOTOS_INCOMPLETE",
                            f"Foto wajib belum lengkap ({detail}). Minta ketua melengkapi, atau terima dengan "
                            "catatan alasan (force).",
                            status=409,
                            details={"items": [{"title": t, "missing": m} for t, m in gaps]},
                        )
                await self.repo.set_status(correction_id, "ACCEPTED", reviewer=reviewer, note=note)
                await self.repo.set_plan_status(row.daily_plan_id, "COMPLETED")
            else:
                await self.repo.set_status(correction_id, "REVISING", reviewer=reviewer, note=note)
        result = await self.repo.get(correction_id)
        titles = {
            "APPROVE": "PM menyetujui koreksi, silakan revisi laporan",
            "REJECT": "PM menolak permintaan koreksi laporan",
            "ACCEPT": "PM menerima revisi laporan Anda",
            "RETURN": "PM mengembalikan laporan untuk direvisi lagi",
        }
        await NotificationService(self.db).notify_employees(
            [row.requested_by_id], "CORRECTION_DECIDED", titles.get(data.decision, "Keputusan koreksi laporan"),
            note or "", target="correction", plan_id=row.daily_plan_id,
        )
        return result

    async def submit_revision(self, user: CurrentUser, correction_id: UUID) -> Any:
        row = await self._locked(correction_id)
        await check_daily_access(self.db, row.daily_plan_id, user, DailyNeed.LEADER)
        if row.status != "REVISING":
            raise AppError("INVALID_STATE", "Koreksi ini belum dibuka untuk revisi.", status=409)
        if not await self.repo.has_report(row.daily_plan_id):
            raise AppError("REPORT_REQUIRED", "Laporan harian wajib diisi sebelum revisi dikirim.", status=422)
        await self.repo.set_status(correction_id, "IN_REVIEW", bump_revision=True)
        notifier = NotificationService(self.db)
        await notifier.notify_division_managers(
            row.requested_by_id, "CORRECTION_REVISED",
            f"{await notifier.employee_name(row.requested_by_id)} mengirim revisi laporan, mohon diperiksa", "",
            target="correction", roles=("PROJECT_MANAGER",),
        )
        return await self.repo.get(correction_id)
