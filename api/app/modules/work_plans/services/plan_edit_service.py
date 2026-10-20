"""
app/modules/work_plans/services/plan_edit_service.py
Draf SK jalur lama: buat (POST /work-plans), ubah (PATCH, EDIT_DRAFT dok 05), tambah hari/tugas, simpan hari
(domain.js SAVE_DAY, V-23). Form lengkap v2 di plan_draft_service. Pesan & kode galat dipertahankan apa adanya.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, ValidationError, db_error, trigger_rule_error
from app.core.permissions import RoleCode, SystemRole
from app.core.security import CurrentUser
from app.modules.work_plans.repositories.plan_edit_repository import CRUDPlanEdit
from app.modules.work_plans.schemas.plan_schema import WorkPlanCreate, WorkPlanUpdate
from app.modules.work_plans.services.plan_assignment_service import PlanAssignmentService
from app.shared.access.access_service import PlanAccess, check_unit_manager, ensure_same_org, require_plan_status
from app.shared.access.plan_access_repository import CRUDPlanAccess

PM_ROLES = (
    RoleCode.PM,
    RoleCode.OPS,
    RoleCode.ADMIN,
    SystemRole.PROJECT_MANAGER,
    SystemRole.OPERATIONAL_MANAGER,
    SystemRole.SUPER_ADMIN,
)


class PlanEditService:
    """Penyusunan draf SK oleh PM unit (jalur lama, masih dipakai klien)."""

    def __init__(self, db: AsyncSession, assignments: PlanAssignmentService) -> None:
        self.db = db
        self.repo = CRUDPlanEdit(db)
        self.assignments = assignments

    async def visible_plans(self, user: CurrentUser, status_filter: str | None, archived: bool) -> list[Any]:
        """SK yang terlihat oleh pengguna (V-07); draf terarsip hanya untuk pengelola (V-21)."""
        return list(
            await CRUDPlanAccess(self.db).visible_plans(user.organization_id, user.user_id, status_filter, archived)
        )

    async def create(self, user: CurrentUser, data: WorkPlanCreate) -> Any:
        """Draf SK baru; ketua (bila ada) langsung jadi anggota. Bentrok jadwal ketua dari trigger → pesan jelas."""
        await check_unit_manager(self.db, data.unit_id, user)
        await ensure_same_org(
            self.db,
            user.organization_id,
            sites=[data.site_id],
            employees=[data.pm_employee_id, data.leader_employee_id],
        )
        await self.assignments.validate_owner(user, data.unit_id, data.pm_employee_id)
        if data.leader_employee_id:
            await self.assignments.validate_team_scope(user, data.unit_id, [data.leader_employee_id])
        try:
            row = await self.repo.insert_plan(
                user.organization_id,
                unit_id=data.unit_id,
                site_id=data.site_id,
                title=data.title,
                location_text=data.location_text,
                description=data.description,
                period_start=data.period_start,
                period_end=data.period_end,
                pm_employee_id=data.pm_employee_id,
                leader_employee_id=data.leader_employee_id,
            )
            if data.leader_employee_id:
                await self.repo.add_leader(row.id, data.leader_employee_id, data.period_start)
        except IntegrityError as e:
            rule = trigger_rule_error(e)
            if rule:
                raise rule from None
            raise db_error(e) from e
        except Exception as e:
            raise db_error(e) from e
        return row

    async def update(self, access: PlanAccess, plan_id: UUID, data: WorkPlanUpdate) -> Any:
        """EDIT_DRAFT: hanya draf, optimistic locking `row_version`; ganti ketua → aturan tim yang sama (R-26)."""
        user = access.user
        await ensure_same_org(self.db, user.organization_id, sites=[data.site_id], employees=[data.leader_employee_id])
        row = await self.repo.draft_state(plan_id, user.organization_id)
        if not row:
            raise AppError("NOT_FOUND", "Rencana Kerja tidak ditemukan.", status=404)
        is_pm = user.role in PM_ROLES
        if row.status != "DRAFT" and not (is_pm and row.status in ("APPROVED", "ONGOING")):
            err_msg = "Hanya rencana kerja berstatus Draf atau yang sedang berjalan yang dapat diubah oleh PM."
            raise AppError("NOT_DRAFT", err_msg)
        if row.row_version != data.row_version:
            raise AppError(
                "CONFLICT",
                "Dokumen ini telah diubah oleh orang lain. Silakan muat ulang halaman.",
                status=409,
            )

        sets: list[str] = []
        params: dict[str, Any] = {}
        for column, key, value in (
            ("title", "title", data.title),
            ("site_id", "site", data.site_id),
            ("location_text", "loc", data.location_text),
            ("description", "desc", data.description),
        ):
            if value is not None:
                sets.append(f"{column} = :{key}")
                params[key] = value
        if data.period_start and data.period_end:
            sets.append("period = daterange(:start, :end, '[]')")
            params.update(start=data.period_start, end=data.period_end)
        if data.leader_employee_id is not None:
            sets.append("leader_employee_id = :leader")
            params["leader"] = data.leader_employee_id
            if data.leader_employee_id != row.leader_employee_id:
                await self.assignments.validate_team_scope(user, row.unit_id, [data.leader_employee_id])
                await self.repo.remove_leader(plan_id)
                try:
                    await self.repo.add_leader(plan_id, data.leader_employee_id, data.period_start or row.period_start)
                except IntegrityError as exc:
                    # Bentrok jadwal ketua (trigger) → 409 berpesan jelas; sebelumnya 500.
                    raise trigger_rule_error(exc) or exc from None
        sets.append("row_version = row_version + 1")

        updated = await self.repo.update_plan(plan_id, user.organization_id, data.row_version, sets, params)
        if not updated:
            raise AppError("CONFLICT", "Gagal update, kemungkinan data diubah secara bersamaan.", status=409)
        return updated

    async def add_day(
        self, access: PlanAccess, plan_id: UUID, work_date: Any, title: str | None, sort_order: int
    ) -> Any:
        """Tambah hari pada draf. → id hari."""
        status = await self.repo.plan_status(plan_id, access.user.organization_id)
        is_pm = access.user.role in PM_ROLES
        if not status or (status != "DRAFT" and not (is_pm and status in ("APPROVED", "ONGOING"))):
            raise AppError("BAD_REQUEST", "Tidak dapat menambah hari. Status rencana kerja bukan DRAFT atau ONGOING.")
        try:
            return await self.repo.insert_day(plan_id, work_date, title, sort_order)
        except SQLAlchemyError:
            raise db_error(Exception("Gagal menambahkan hari (mungkin tanggal bentrok).")) from None

    async def add_task(self, day_id: UUID, title: str, sort_order: int) -> Any:
        """Tambah tugas pada hari. → id tugas."""
        return await self.repo.insert_task(day_id, title, sort_order)

    async def save_day(
        self, access: PlanAccess, day_id: UUID, title: str, task_titles: list[str]
    ) -> tuple[str, list[str]]:
        """domain.js SAVE_DAY (V-23): selagi draf atau oleh PM saat ongoing (1–30 tugas). → (judul, tugas)."""
        is_pm = access.user.role in PM_ROLES
        if not (is_pm and access.plan.status in ("APPROVED", "ONGOING")):
            require_plan_status(access, PlanStatus.DRAFT)
        if not 1 <= len(task_titles) <= 30:
            raise ValidationError("Isi antara 1 sampai 30 tugas per hari.")
        titles = [t.strip() for t in task_titles]
        if not title.strip() or not all(titles):
            raise ValidationError("Judul hari dan setiap tugas wajib diisi.")
        await self.repo.replace_day_plan(day_id, title.strip(), titles)
        return title.strip(), titles

    async def reschedule_item(
        self,
        user: CurrentUser,
        item_id: UUID,
        target_daily_plan_id: UUID,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        location_name: str | None = None,
        site_lat: float | None = None,
        site_lng: float | None = None,
        assigned_employee_ids: list[str] | None = None,
    ) -> Any:
        """domain.js RESCHEDULE_TASK (PM Full Override): Pindahkan item penugasan ke slot waktu/hari lain."""
        import json
        emp_json = json.dumps(assigned_employee_ids) if assigned_employee_ids else None
        res = await self.repo.reschedule_item(
            item_id,
            target_daily_plan_id,
            start_time=start_time,
            end_time=end_time,
            location_name=location_name,
            site_lat=site_lat,
            site_lng=site_lng,
            assigned_employee_ids=emp_json,
        )
        if not res:
            raise AppError("NOT_FOUND", "Item tugas tidak ditemukan.", status=404)
        return res
