"""
app/services/plan_edit_service.py
Draf SK jalur lama: buat (POST /work-plans), ubah (PATCH, EDIT_DRAFT dok 05), tambah hari/tugas, simpan hari
(domain.js SAVE_DAY, V-23). Form lengkap v2 di plan_draft_service. Pesan & kode galat dipertahankan apa adanya.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import ValidationError, trigger_rule_error
from app.core.security import CurrentUser
from app.crud.crud_plan_access import CRUDPlanAccess
from app.crud.crud_plan_edit import CRUDPlanEdit
from app.schemas.plan import WorkPlanCreate, WorkPlanUpdate
from app.services.access_service import PlanAccess, check_unit_manager, ensure_same_org, require_plan_status
from app.services.plan_assignment_service import PlanAssignmentService


def _db_error(e: Exception) -> HTTPException:
    # Pesan DB_ERROR diganti teks umum oleh handler galat; isi aslinya hanya ke log (T-06).
    return HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})


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
            raise _db_error(e) from e
        except Exception as e:
            raise _db_error(e) from e
        return row

    async def update(self, access: PlanAccess, plan_id: UUID, data: WorkPlanUpdate) -> Any:
        """EDIT_DRAFT: hanya draf, optimistic locking `row_version`; ganti ketua → aturan tim yang sama (R-26)."""
        user = access.user
        await ensure_same_org(self.db, user.organization_id, sites=[data.site_id], employees=[data.leader_employee_id])
        row = await self.repo.draft_state(plan_id, user.organization_id)
        if not row:
            raise HTTPException(status_code=404, detail="Rencana Kerja tidak ditemukan.")
        if row.status != "DRAFT":
            raise HTTPException(
                status_code=400,
                detail={"code": "NOT_DRAFT", "message": "Hanya rencana kerja berstatus Draf yang dapat diubah."},
            )
        if row.row_version != data.row_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CONFLICT",
                    "message": "Dokumen ini telah diubah oleh orang lain. Silakan muat ulang halaman.",
                },
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
            raise HTTPException(
                status_code=409,
                detail={"code": "CONFLICT", "message": "Gagal update, kemungkinan data diubah secara bersamaan."},
            )
        return updated

    async def add_day(
        self, access: PlanAccess, plan_id: UUID, work_date: Any, title: str | None, sort_order: int
    ) -> Any:
        """Tambah hari pada draf. → id hari."""
        status = await self.repo.plan_status(plan_id, access.user.organization_id)
        if not status or status != "DRAFT":
            raise HTTPException(status_code=400, detail="Tidak dapat menambah hari. Status rencana kerja bukan DRAFT.")
        try:
            return await self.repo.insert_day(plan_id, work_date, title, sort_order)
        except SQLAlchemyError:
            raise HTTPException(
                status_code=400,
                detail={"code": "DB_ERROR", "message": "Gagal menambahkan hari (mungkin tanggal bentrok)."},
            ) from None

    async def add_task(self, day_id: UUID, title: str, sort_order: int) -> Any:
        """Tambah tugas pada hari. → id tugas."""
        return await self.repo.insert_task(day_id, title, sort_order)

    async def save_day(
        self, access: PlanAccess, day_id: UUID, title: str, task_titles: list[str]
    ) -> tuple[str, list[str]]:
        """domain.js SAVE_DAY (V-23): selagi draf, 1–30 tugas, judul hari & tugas wajib. → (judul, tugas)."""
        require_plan_status(access, PlanStatus.DRAFT)
        if not 1 <= len(task_titles) <= 30:
            raise ValidationError("Isi antara 1 sampai 30 tugas per hari.")
        titles = [t.strip() for t in task_titles]
        if not title.strip() or not all(titles):
            raise ValidationError("Judul hari dan setiap tugas wajib diisi.")
        await self.repo.replace_day_plan(day_id, title.strip(), titles)
        return title.strip(), titles
