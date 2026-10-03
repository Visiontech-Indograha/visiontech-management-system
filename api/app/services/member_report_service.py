"""
app/services/member_report_service.py
Laporan harian berjenjang (alur SK v2 PR2, flowchart SK2-E): anggota menulis & mengirim laporannya ke ketua;
ketua menghimpunnya menjadi laporan harian untuk PM. Juga dokumen A4 laporan harian/mingguan.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.crud.crud_member_report import CRUDMemberReport
from app.crud.crud_org_clock import CRUDOrgClock
from app.services.access_service import PlanAccess, ensure_same_org, require_plan_status
from app.services.notification_service import NotificationService
from app.services.pdf_service import render_report_html


class MemberReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDMemberReport(db)

    async def _me(self, access: PlanAccess) -> str:
        employee = await self.repo.employee_of(access.user.user_id)
        if employee is None:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan.")
        return employee

    async def _editable(self, access: PlanAccess, day_id: UUID) -> str:
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        if not await CRUDOrgClock(self.db).day_reached(day_id):
            raise ValidationError("Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.")
        return await self._me(access)

    async def list_for_day(self, day_id: UUID) -> list[Any]:
        return await self.repo.list_for_day(day_id)

    async def mine(self, access: PlanAccess, day_id: UUID) -> Any:
        return await self.repo.mine(day_id, await self._me(access))

    async def save(self, access: PlanAccess, day_id: UUID, body: str, obstacle: str, file_ids: list[UUID]) -> Any:
        """Anggota menyimpan draf laporannya (selama belum dikirim ke ketua)."""
        employee = await self._editable(access, day_id)
        await ensure_same_org(self.db, access.user.organization_id, files=file_ids)
        row = await self.repo.save(day_id, employee, body.strip(), obstacle.strip())
        if row is None:
            raise AppError("INVALID_STATE", "Laporan yang sudah dikirim ke ketua tidak dapat diubah.", status=409)
        await self.repo.replace_evidence(row.id, file_ids)
        return await self.repo.mine(day_id, employee)

    async def send(self, access: PlanAccess, day_id: UUID) -> Any:
        """Anggota mengirim laporannya ke ketua tim; ketua mendapat notifikasi."""
        employee = await self._editable(access, day_id)
        current = await self.repo.mine(day_id, employee)
        if current is None:
            raise AppError("INVALID_STATE", "Simpan laporan dulu sebelum mengirim.", status=409)
        if current.status == "SENT":
            raise AppError("INVALID_STATE", "Laporan sudah dikirim ke ketua.", status=409)
        if len(current.body.strip()) < 10:
            raise ValidationError("Uraian laporan minimal 10 karakter.")
        await self.repo.send(day_id, employee)
        day = await self.repo.day_info(day_id)
        await NotificationService(self.db).member_report_sent(access.plan.id, current.full_name, day.work_date)
        return await self.repo.mine(day_id, employee)

    # ── Dokumen A4 laporan (dibaca di web & HP; PDF di server memakai templat yang sama) ─────────
    async def daily_report_html(self, access: PlanAccess, day_id: UUID) -> str:
        report = await self.repo.daily_report_doc(day_id)
        if report is None:
            raise NotFoundError("Laporan harian")
        members = await self.repo.list_for_day(day_id)
        header = await self.repo.plan_header(access.plan.id)
        return render_report_html("Laporan harian", header, report,
                                  period=report.work_date, members=[m for m in members if m.status == "SENT"])

    async def weekly_report_html(self, access: PlanAccess, name: str) -> str:
        report = await self.repo.weekly_report_doc(access.plan.id, name)
        if report is None:
            raise NotFoundError("Laporan mingguan")
        header = await self.repo.plan_header(access.plan.id)
        return render_report_html(report.name, header, report, period=(report.starts_on, report.ends_on), members=[])
