"""
app/modules/work_plans/services/daily_plan_service.py
Jadwal harian daily-first (Milestone 5, docs/35 §3; keputusan pemilik 2026-10-20). Minggu = rentang tanggal.

- Membuat & mengubah: PM/OM divisi (SUPER_ADMIN semua). Tim harus milik divisi itu; satu jadwal per tim per tanggal;
  tanggal tidak boleh lampau. Ubah hanya saat DRAFT/SUBMITTED.
- Status: DRAFT → (ajukan) SUBMITTED → (setujui PM) APPROVED → (ketua mulai, pada/after tanggalnya) ONGOING →
  (ketua/PM selesai) COMPLETED. Tolak: SUBMITTED → DRAFT + alasan. PM boleh langsung menyetujui DRAFT
  (persetujuan per hari atau sekaligus satu minggu lewat matriks).
- Lapangan (ketua/anggota) hanya melihat jadwal yang sudah disetujui.
- Hapus: hanya DRAFT/SUBMITTED yang belum dipakai absensi/peminjaman aset; item ikut terarsip.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.work_plans.repositories.daily_plan_repository import DailyPlanRepository
from app.modules.work_plans.schemas.daily_plan_schema import DailyPlanCreate, DailyPlanUpdate
from app.shared.access.access_service import (
    DailyAccess,
    DailyNeed,
    check_daily_access,
    check_division_manager,
    is_admin,
    require_daily_status,
)

EDITABLE = ("DRAFT", "SUBMITTED")
FIELD_ROLES = ("TEAM_LEADER", "EMPLOYEE")


def _week(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


class DailyPlanService:
    """Use case jadwal harian."""

    def __init__(self, db: AsyncSession, repo: DailyPlanRepository) -> None:
        self.db = db
        self.repo = repo

    @staticmethod
    def _manager_scope(user: CurrentUser) -> str | None:
        """employee_id PM/OM yang dibatasi ke divisinya; None = SUPER_ADMIN/HR (semua)."""
        if is_admin(user) or user.role == "ADMIN_HR_GA":
            return None
        return user.employee_id or "00000000-0000-0000-0000-000000000000"

    async def access(self, user: CurrentUser, daily_plan_id: UUID, need: DailyNeed) -> DailyAccess:
        return await check_daily_access(self.db, daily_plan_id, user, need)

    # ── Baca ──────────────────────────────────────────────────────────────────
    async def list_plans(
        self, user: CurrentUser, *, start: date | None, end: date | None, division_id: UUID | None,
        team_id: UUID | None, status: str | None,
    ) -> list[Any]:
        if start is None or end is None:
            start, end = _week(jakarta_now().date())
        if end < start or (end - start).days > 62:
            raise ValidationError("Rentang tanggal tidak valid (maksimal 62 hari).")
        field = user.role in FIELD_ROLES
        return await self.repo.list_plans(
            start=start, end=end, division_id=division_id, team_id=team_id, status=status,
            managed_by=None if field else self._manager_scope(user),
            field_employee=(user.employee_id or "00000000-0000-0000-0000-000000000000") if field else None,
        )

    async def detail(self, daily_plan_id: UUID) -> dict[str, Any]:
        row = await self.repo.get(daily_plan_id)
        if row is None:
            raise NotFoundError("Jadwal harian")
        data = dict(row._mapping)
        data["items"] = [dict(i._mapping) for i in await self.repo.items(daily_plan_id)]
        data["attachment_file_ids"] = await self.repo.attachment_ids(daily_plan_id)
        return data

    async def form_options(self, user: CurrentUser) -> dict[str, Any]:
        scope = self._manager_scope(user)
        return {
            "divisions": [dict(r._mapping) for r in await self.repo.divisions(scope)],
            "teams": [dict(r._mapping) for r in await self.repo.teams(scope)],
            "orders": [dict(r._mapping) for r in await self.repo.open_orders(scope)],
        }

    async def plans_of_order(self, user: CurrentUser, completion_id: UUID) -> list[Any]:
        rows = await self.repo.plans_of_order(completion_id)
        visible = []
        for row in rows:
            try:
                await check_daily_access(self.db, row.daily_plan_id, user, DailyNeed.VIEW)
                visible.append(row)
            except (NotFoundError, AppError):
                continue
        return visible

    # ── Tulis ─────────────────────────────────────────────────────────────────
    async def _check_team_day(self, division_id: UUID, team_id: UUID, work_date: date, exclude: UUID | None) -> None:
        if not await self.repo.team_of_division(team_id, division_id):
            raise ValidationError("Tim tidak ditemukan, nonaktif, atau bukan milik divisi ini.")
        if work_date < jakarta_now().date():
            raise ValidationError("Tanggal jadwal tidak boleh sebelum hari ini.")
        if await self.repo.team_day_taken(team_id, work_date, exclude):
            raise AppError("TEAM_DAY_TAKEN", "Tim ini sudah punya jadwal pada tanggal tersebut.", status=409)

    async def _check_project(self, project_id: UUID | None, division_id: Any, work_date: date) -> None:
        """Proyek jadwal: divisi sama, sedang berjalan, dan tanggal jadwal di dalam masa proyek."""
        if project_id is None:
            return
        project = await self.repo.project_window(project_id)
        if project is None or str(project.division_id) != str(division_id):
            raise ValidationError("Proyek tidak ditemukan di divisi jadwal ini.")
        if project.status != "ONGOING":
            raise ValidationError("Proyek tidak sedang berjalan.")
        if not project.start_date <= work_date <= project.end_date:
            raise ValidationError("Tanggal jadwal di luar masa proyek.")

    async def create(self, user: CurrentUser, data: DailyPlanCreate) -> Any:
        await check_division_manager(self.db, data.division_id, user)
        await self._check_team_day(data.division_id, data.team_id, data.work_date, None)
        await self._check_project(data.project_id, data.division_id, data.work_date)
        if not user.employee_id:
            raise ValidationError("Akun ini belum terhubung ke data karyawan; jadwal butuh pembuat yang tercatat.")
        fields = data.model_dump()
        fields.update(division_id=str(data.division_id), team_id=str(data.team_id), created_by_id=user.employee_id,
                      site_name=data.site_name.strip(), project_id=str(data.project_id) if data.project_id else None)
        return await self.repo.get(await self.repo.insert(fields))

    async def update(self, user: CurrentUser, daily_plan_id: UUID, data: DailyPlanUpdate) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        plan = access.plan
        if data.team_id or data.work_date:
            await self._check_team_day(plan.division_id, data.team_id or plan.team_id,
                                       data.work_date or plan.work_date, daily_plan_id)
        current = await self.repo.get(daily_plan_id)
        if data.project_id or (data.work_date and current.project_id):
            await self._check_project(data.project_id or current.project_id, plan.division_id,
                                      data.work_date or plan.work_date)
        clock_in = data.clock_in_time or current.clock_in_time
        clock_out = data.clock_out_time or current.clock_out_time
        if clock_out <= clock_in:
            raise ValidationError("Jam pulang harus setelah jam masuk.")
        fields = data.model_dump()
        fields.update(team_id=str(data.team_id) if data.team_id else None,
                      project_id=str(data.project_id) if data.project_id else None,
                      site_name=data.site_name.strip() if data.site_name else None)
        await self.repo.update(daily_plan_id, fields)
        return await self.repo.get(daily_plan_id)

    async def copy(self, user: CurrentUser, daily_plan_id: UUID, work_dates: list[date]) -> list[Any]:
        """Salin lokasi, jam, & tim ke tanggal lain sebagai DRAFT (item tidak ikut — dijadwalkan per hari)."""
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        source = await self.repo.get(daily_plan_id)
        created = []
        for work_date in sorted(set(work_dates)):
            await self._check_team_day(access.plan.division_id, source.team_id, work_date, None)
            await self._check_project(source.project_id, source.division_id, work_date)
            fields = {k: getattr(source, k) for k in ("work_date", "site_name", "site_lat", "site_lng",
                                                      "attendance_radius_m", "clock_in_time", "clock_out_time")}
            fields.update(work_date=work_date, division_id=str(source.division_id), team_id=str(source.team_id),
                          created_by_id=user.employee_id,
                          project_id=str(source.project_id) if source.project_id else None)
            created.append(await self.repo.get(await self.repo.insert(fields)))
        return created

    async def delete(self, user: CurrentUser, daily_plan_id: UUID) -> None:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        if await self.repo.has_activity(daily_plan_id):
            raise AppError("DAILY_PLAN_IN_USE", "Jadwal sudah dipakai absensi atau peminjaman aset.", status=409)
        await self.repo.archive(daily_plan_id)

    async def set_attachments(self, user: CurrentUser, daily_plan_id: UUID, file_ids: list[UUID]) -> list[UUID]:
        await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        if await self.repo.existing_files(file_ids) != len(set(file_ids)):
            raise ValidationError("Ada berkas lampiran yang belum diunggah atau sudah dihapus.")
        await self.repo.replace_attachments(daily_plan_id, file_ids)
        return await self.repo.attachment_ids(daily_plan_id)

    # ── Status ────────────────────────────────────────────────────────────────
    async def submit(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, "DRAFT")
        await self.repo.set_status(daily_plan_id, "SUBMITTED")
        return await self.repo.get(daily_plan_id)

    async def approve(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        if access.plan.work_date < jakarta_now().date():
            raise ValidationError("Jadwal untuk tanggal yang sudah lewat tidak dapat disetujui.")
        await self.repo.set_status(daily_plan_id, "APPROVED", approver=user.employee_id)
        return await self.repo.get(daily_plan_id)

    async def bulk_approve(self, user: CurrentUser, daily_plan_ids: list[UUID]) -> dict[str, list[UUID]]:
        """Persetujuan matriks mingguan: yang tidak berwenang/berstatus salah dilewati, bukan menggagalkan semua."""
        approved, skipped = [], []
        for daily_plan_id in dict.fromkeys(daily_plan_ids):
            try:
                await self.approve(user, daily_plan_id)
                approved.append(daily_plan_id)
            except AppError:
                skipped.append(daily_plan_id)
        return {"approved": approved, "skipped": skipped}

    async def reject(self, user: CurrentUser, daily_plan_id: UUID, reason: str) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, "SUBMITTED", "APPROVED")
        await self.repo.set_status(daily_plan_id, "DRAFT", rejection_reason=reason.strip())
        return await self.repo.get(daily_plan_id)

    async def start(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.LEADER)
        require_daily_status(access, "APPROVED")
        if access.plan.work_date > jakarta_now().date():
            raise ValidationError("Jadwal baru bisa dimulai pada tanggalnya.")
        await self.repo.set_status(daily_plan_id, "ONGOING")
        return await self.repo.get(daily_plan_id)

    async def complete(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.VIEW)
        if not (access.is_leader or access.manages):
            raise AppError("FORBIDDEN", "Hanya ketua tim atau PM/OM divisi yang dapat menutup jadwal.", status=403)
        require_daily_status(access, "ONGOING")
        await self.repo.set_status(daily_plan_id, "COMPLETED")
        return await self.repo.get(daily_plan_id)
