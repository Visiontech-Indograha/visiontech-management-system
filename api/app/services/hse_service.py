"""
app/services/hse_service.py
domain.js REPORT/RESOLVE_INCIDENT, SAVE/SUBMIT/REVIEW_REPORT, TOGGLE_TASK. Akses SK diperiksa dependency
(`plan_day_access`, `incident_plan_access`) atau `check_plan_access`; aturan status & tanggal di sini.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import RoleCode
from app.core.security import CurrentUser
from app.crud.crud_hse import CRUDHse
from app.crud.crud_org_clock import CRUDOrgClock
from app.schemas.work_type import EvidenceIn, merge_evidence
from app.services.access_service import PlanAccess, PlanNeed, check_plan_access, ensure_same_org, require_plan_status
from app.services.notification_service import NotificationService
from app.services.work_type_service import WorkTypeService


class HseService:
    """Insiden K3 dan laporan harian ketua tim."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDHse(db)
        self.clock = CRUDOrgClock(db)
        self.notifications = NotificationService(db)

    async def _ensure_day_reached(self, day_id: UUID) -> None:
        """R6 · laporan hanya pada atau setelah tanggal pelaksanaan (tanggal server, zona organisasi, V-10)."""
        if not await self.clock.day_reached(day_id):
            raise ValidationError("Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.")

    async def list_incidents(self, user: CurrentUser, plan_id: UUID) -> list[Any]:
        """Insiden satu SK; SK asing/tak terlihat → 404."""
        await check_plan_access(self.db, plan_id, user, PlanNeed.VIEW)
        return await self.repo.incidents_of_plan(plan_id, user.organization_id)

    async def report_incident(
        self,
        user: CurrentUser,
        plan_id: UUID,
        category: str,
        severity: str,
        description: str,
        evidence_file_ids: list[UUID],
    ) -> Any:
        """domain.js REPORT_INCIDENT: ketua/anggota SK yang sedang berjalan (V-09, V-11). Tanggal insiden = hari
        ini menurut server & zona organisasi (V-10) — tanggal kiriman klien tidak dipakai."""
        standing = await check_plan_access(self.db, plan_id, user, PlanNeed.LEADER_OR_MEMBER)
        require_plan_status(standing, PlanStatus.IN_PROGRESS)
        await ensure_same_org(self.db, user.organization_id, files=evidence_file_ids)
        employee_id = await self.repo.employee_of_user(user.user_id)
        today = (await self.clock.local_now(user.organization_id)).today
        incident = await self.repo.insert_incident(
            user.organization_id, plan_id, employee_id, today, category, severity, description
        )
        if evidence_file_ids:
            await self.repo.add_incident_evidence(incident.id, [str(f) for f in evidence_file_ids])
        return incident

    async def resolve_incident(self, access: PlanAccess, incident_id: UUID, note: str | None) -> Any:
        """domain.js RESOLVE_INCIDENT: PM (unit SK), OPS, ASSET. R2: PM unit lain tidak melihat SK ini → 404."""
        user = access.user
        if not (access.manages or RoleCode.ASSET in user.roles):
            raise ForbiddenError("Hanya PM unit pekerjaan ini atau petugas aset yang dapat menyelesaikan insiden.")
        employee_id = await self.repo.employee_of_user(user.user_id)
        row = await self.repo.resolve_incident(incident_id, user.organization_id, employee_id, note)
        if not row:
            raise HTTPException(status_code=404, detail="Insiden tidak ditemukan.")
        return row

    async def save_daily_report(
        self,
        access: PlanAccess,
        day_id: UUID,
        body: str | None,
        obstacle: str | None,
        evidence_file_ids: list[UUID],
        evidence: list[EvidenceIn] | None = None,
    ) -> Any:
        """domain.js SAVE_REPORT (V-11, V-24): ketua, SK berjalan, hari sudah tiba, laporan belum diserahkan."""
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        await self._ensure_day_reached(day_id)
        items = merge_evidence(evidence_file_ids, evidence or [])
        await ensure_same_org(self.db, access.user.organization_id, files=[UUID(i[0]) for i in items])
        report = await self.repo.upsert_daily_report(day_id, body, obstacle)
        if report is None:
            raise AppError("INVALID_STATE", "Laporan yang sudah diserahkan tidak dapat diubah.", status=409)
        if items:
            await self.repo.replace_report_evidence(report.id, items)
        return report

    async def submit_daily_report(self, access: PlanAccess, day_id: UUID) -> Any:
        """domain.js SUBMIT_REPORT (V-24): dari DRAFT atau setelah dikembalikan PM; PM diberi tahu."""
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        await self._ensure_day_reached(day_id)
        employee_id = await self.repo.employee_of_user(access.user.user_id)
        body = await self.repo.daily_report_body(day_id)
        if body is not None and len(body.strip()) < 10:
            raise ValidationError("Uraian pekerjaan minimal 10 karakter sebelum laporan dikirim.")
        await WorkTypeService(self.db).ensure_daily_complete(access.plan.id, day_id)  # T9: slot foto wajib
        try:
            report = await self.repo.submit_daily_report(day_id, employee_id)
        except Exception as e:
            if "check" in str(e).lower():
                raise HTTPException(status_code=400, detail="Laporan terlalu singkat (minimal 10 karakter).") from e
            raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)}) from e
        if not report:
            raise AppError("INVALID_STATE", "Laporan sudah diserahkan atau belum dibuat.", status=409)
        await self.notifications.report_submitted(access.plan.id, "Laporan harian", bool(report.resubmitted))
        return report

    async def review_daily_report(self, access: PlanAccess, day_id: UUID, decision: str, note: str | None) -> Any:
        """domain.js REVIEW_REPORT (V-24): PM unit/OPS menyetujui atau mengembalikan (wajib catatan)."""
        require_plan_status(access, PlanStatus.IN_PROGRESS, PlanStatus.COMPLETION_REVIEW)
        if decision not in ("APPROVE", "RETURN"):
            raise ValidationError("Pilihan keputusan tidak dikenali. Muat ulang, lalu pilih lagi.")
        note = (note or "").strip()
        if decision == "RETURN" and not note:
            raise ValidationError("Catatan revisi wajib diisi.")
        status = "APPROVED" if decision == "APPROVE" else "CHANGES_REQUESTED"
        report = await self.repo.review_daily_report(day_id, status, note or None, access.user.user_id)
        if report is None:
            raise AppError("INVALID_STATE", "Laporan belum menunggu pemeriksaan.", status=409)
        await self.notifications.report_reviewed(access.plan.id, "Laporan harian", decision == "APPROVE", note or None)
        return report

    async def toggle_task(self, access: PlanAccess, day_id: UUID, task_id: UUID) -> Any:
        """domain.js TOGGLE_TASK (V-23): ketua mencentang tugas hari itu selama laporan belum diserahkan."""
        require_plan_status(access, PlanStatus.IN_PROGRESS)
        await self._ensure_day_reached(day_id)
        if await self.repo.daily_report_status(day_id) in ("SUBMITTED", "APPROVED"):
            raise AppError("INVALID_STATE", "Daftar tugas tidak dapat diubah setelah laporan diserahkan.", status=409)
        row = await self.repo.toggle_task(task_id, day_id, access.user.user_id)
        if row is None:
            raise NotFoundError("Tugas")
        return row
