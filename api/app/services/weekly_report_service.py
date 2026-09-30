"""
app/services/weekly_report_service.py
Laporan mingguan (V-25) — padanan `domain.js` SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY.
Ketua menurut SK mengisi & menyerahkan; PM unit/OPS memeriksa. Kewenangan dicek penjaga V-07 di router.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PlanAccess, require_plan_status
from app.core.enums import PlanStatus
from app.core.errors import AppError, NotFoundError, ValidationError
from app.repositories.weekly_report_repo import WeeklyReportRepo

EDITABLE = ("DRAFT", "CHANGES_REQUESTED")


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class WeeklyReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = WeeklyReportRepo(db)

    async def list_weeks(self, access: PlanAccess) -> list[Any]:
        return await self.repo.list_weeks(access.plan.id)

    async def _week(self, access: PlanAccess, week: int) -> Any:
        row = await self.repo.get_week(access.plan.id, week)
        if row is None:
            raise NotFoundError("Minggu")
        return row

    async def _editable_week(self, access: PlanAccess, week: int) -> Any:
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        row = await self._week(access, week)
        if row.status not in EDITABLE:
            raise _state("Laporan mingguan sudah diserahkan.")
        return row

    async def save_weekly(self, access: PlanAccess, week: int, body: str, obstacle: str) -> Any:
        row = await self._editable_week(access, week)
        await self.repo.save(access.plan.id, row, body.strip(), obstacle.strip())
        return await self._week(access, week)

    async def submit_weekly(self, access: PlanAccess, week: int) -> Any:
        row = await self._editable_week(access, week)
        if not row.days_approved:
            raise _state("Semua laporan harian dalam minggu ini harus disetujui terlebih dahulu.")
        if len(row.body) <= 10:
            raise ValidationError("Laporan mingguan wajib diisi.")
        if not row.obstacle:
            raise ValidationError('Ringkasan kendala mingguan wajib diisi (isi "Tidak ada" jika lancar).')
        await self.repo.submit(access.plan.id, row.name, access.user.user_id)
        return await self._week(access, week)

    async def review_weekly(self, access: PlanAccess, week: int, decision: str, note: str | None) -> Any:
        require_plan_status(access, PlanStatus.IN_PROGRESS, PlanStatus.COMPLETION_REVIEW)
        if decision not in ("APPROVE", "RETURN"):
            raise ValidationError("Keputusan tidak valid.")
        clean_note = (note or "").strip()
        if decision == "RETURN" and not clean_note:
            raise ValidationError("Catatan revisi wajib diisi.")
        row = await self._week(access, week)
        status = "APPROVED" if decision == "APPROVE" else "CHANGES_REQUESTED"
        if await self.repo.review(access.plan.id, row.name, status, clean_note or None, access.user.user_id) is None:
            raise _state("Laporan mingguan belum menunggu pemeriksaan.")
        return await self._week(access, week)
