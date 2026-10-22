"""
app/modules/work_plans/services/plan_item_service.py
Item per titik, prasyarat, progres, dan rollover (Milestone 6, docs/35 §3–4; keputusan pemilik 2026-10-20).

Susun item (PM/OM divisi, jadwal DRAFT/SUBMITTED):
- jenis pekerjaan (template) milik divisi jadwal; order klien (bila ada) di divisi yang sama & masih terbuka;
- prasyarat (`depends_on_item_id`) = item lain pada tanggal ≤ jadwal ini: tim yang sama & order yang sama, ATAU
  lintas tim/divisi di lokasi yang sama (nama lokasi jadwal & klien order sama) — mis. kabel ACS menunggu galian
  parit tim CCTV; tim lain hanya melihat statusnya;
- penugasan (`assigned_employee_ids`) hanya anggota aktif tim jadwal.
Progres (tim, jadwal ONGOING): tidak boleh melebihi target; prasyarat harus DONE dulu; DONE butuh semua foto wajib
(image_requirement jenis pekerjaan) terpenuhi.
Rollover: ketua mengajukan (PENDING_ROLLOVER / WAITING_PM, delay_reason, progres parsial) → PM/OM divisi memutus:
- tujuan = jadwal yang ada ATAU tanggal baru (jadwal dibuat otomatis, menyalin divisi/tim/lokasi/jam, disetujui);
- tanggal tujuan > tanggal asal; tim & divisi sama; sisa volume terbawa (target baru = target - selesai);
- hanya item aktif terakhir rantai yang bisa digeser (SHIFTED_DAY tidak bisa digeser lagi);
- delay_reason ketua tidak ditimpa — catatan PM ke app_activity_logs.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.work_plans.repositories.plan_item_repository import PlanItemRepository
from app.modules.work_plans.schemas.plan_item_schema import (
    PlanItemCreate,
    PlanItemUpdate,
    ProgressIn,
    RolloverDecision,
    RolloverRequest,
)
from app.shared.access.access_service import DailyAccess, DailyNeed, check_daily_access, require_daily_status

EDITABLE = ("DRAFT", "SUBMITTED")
FIELD_ACTIVE = ("APPROVED", "ONGOING")


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class PlanItemService:
    """Use case item pekerjaan per titik."""

    def __init__(self, db: AsyncSession, repo: PlanItemRepository) -> None:
        self.db = db
        self.repo = repo

    async def _item(self, user: CurrentUser, item_id: UUID, need: DailyNeed) -> tuple[Any, DailyAccess]:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError("Item pekerjaan")
        access = await check_daily_access(self.db, item.daily_plan_id, user, need)
        return item, access

    # ── Baca ──────────────────────────────────────────────────────────────────
    async def list_of_daily(self, user: CurrentUser, daily_plan_id: UUID) -> list[Any]:
        await check_daily_access(self.db, daily_plan_id, user, DailyNeed.VIEW)
        return await self.repo.of_daily(daily_plan_id)

    async def get(self, user: CurrentUser, item_id: UUID) -> Any:
        return (await self._item(user, item_id, DailyNeed.VIEW))[0]

    async def chain(self, user: CurrentUser, item_id: UUID) -> list[Any]:
        await self._item(user, item_id, DailyNeed.VIEW)
        return await self.repo.chain(item_id)

    async def prerequisite_options(self, user: CurrentUser, daily_plan_id: UUID) -> list[Any]:
        """Calon prasyarat untuk item baru di jadwal ini (pengelola jadwal)."""
        await check_daily_access(self.db, daily_plan_id, user, DailyNeed.MANAGE)
        return await self.repo.prerequisite_options(daily_plan_id)

    # ── Susun ─────────────────────────────────────────────────────────────────
    async def _validate(self, access: DailyAccess, fields: dict[str, Any], item_id: UUID | None = None) -> None:
        plan = access.plan
        if fields.get("work_type_id") and await self.repo.work_type_division(fields["work_type_id"]) != str(
                plan.division_id):
            raise ValidationError("Jenis pekerjaan tidak ditemukan atau bukan template divisi jadwal ini.")
        if fields.get("completion_id"):
            order = await self.repo.order_division(fields["completion_id"])
            if order is None or not order.open:
                raise ValidationError("Order klien tidak ditemukan atau sudah selesai/dibatalkan.")
            if order.division_id not in (None, str(plan.division_id)):
                raise ValidationError("Order klien bukan milik divisi jadwal ini.")
        dep_id = fields.get("depends_on_item_id")
        if dep_id:
            if item_id and str(dep_id) == str(item_id):
                raise ValidationError("Pekerjaan tidak boleh menunggu dirinya sendiri.")
            dep = await self.repo.prerequisite(dep_id)
            if dep is None or dep.work_date > plan.work_date:
                raise ValidationError("Pekerjaan yang ditunggu harus di tanggal ini atau sebelumnya.")
            order_id = fields.get("completion_id")
            if str(dep.team_id) == str(plan.team_id):
                if order_id and dep.completion_id and str(dep.completion_id) != str(order_id):
                    raise ValidationError("Pekerjaan yang ditunggu harus dari pekerjaan klien yang sama.")
            else:
                # Lintas tim/divisi: hanya di lokasi yang sama untuk klien yang sama.
                site = (await self.repo.plan_site(plan.daily_plan_id) or "").strip().lower()
                client = (await self.repo.order_client(order_id) or "").strip().lower() if order_id else ""
                if not site or site != (dep.site_name or "").strip().lower() or (
                        client and client != (dep.client_name or "").strip().lower()):
                    raise ValidationError("Pekerjaan tim lain yang ditunggu harus di lokasi & klien yang sama.")
        assigned = fields.get("assigned_employee_ids")
        if assigned:
            members = await self.repo.team_members(plan.team_id)
            if not {str(e) for e in assigned} <= members:
                raise ValidationError("Penugasan hanya untuk anggota aktif tim jadwal ini.")

    async def create(self, user: CurrentUser, daily_plan_id: UUID, data: PlanItemCreate) -> Any:
        access = await check_daily_access(self.db, daily_plan_id, user, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        fields = data.model_dump()
        fields["title"] = data.title.strip()
        await self._validate(access, fields)
        return await self.repo.get(await self.repo.insert(daily_plan_id, fields))

    async def update(self, user: CurrentUser, item_id: UUID, data: PlanItemUpdate) -> Any:
        item, access = await self._item(user, item_id, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        fields = data.model_dump(exclude_unset=True)
        if fields.get("title"):
            fields["title"] = fields["title"].strip()
        phase = fields.get("task_phase", item.task_phase)
        main = fields.get("is_main_deliverable", item.is_main_deliverable)
        if main and phase not in ("INSTALLATION", "REPLACEMENT", "MAINTENANCE"):
            raise ValidationError("Deliverable utama hanya untuk fase instalasi, penggantian, atau pemeliharaan.")
        await self._validate(access, {"completion_id": item.completion_id, **fields}, item_id)
        await self.repo.update(item_id, fields)
        return await self.repo.get(item_id)

    async def delete(self, user: CurrentUser, item_id: UUID) -> None:
        _, access = await self._item(user, item_id, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        if await self.repo.dependents(item_id):
            raise AppError("ITEM_IS_PREREQUISITE", "Pekerjaan ini masih ditunggu pekerjaan lain.", status=409)
        await self.repo.archive(item_id)

    # ── Lapangan ──────────────────────────────────────────────────────────────
    async def progress(self, user: CurrentUser, item_id: UUID, data: ProgressIn) -> Any:
        item, access = await self._item(user, item_id, DailyNeed.TEAM)
        require_daily_status(access, "ONGOING")
        if item.status in ("PENDING_ROLLOVER", "SHIFTED_DAY"):
            raise _state("Pekerjaan ini sudah dipindah ke hari lain; catat hasilnya di hari baru.")
        if data.completed_qty > item.target_qty:
            raise ValidationError("Volume selesai melebihi target item.")
        if item.depends_on_item_id and data.completed_qty > 0:
            dep = await self.repo.prerequisite(item.depends_on_item_id)
            if dep is not None and not dep.done:
                owner = f" — dikerjakan {dep.team_name}" if str(dep.team_id) != str(access.plan.team_id) else ""
                raise AppError("PREREQUISITE_NOT_DONE",
                               f"Tunggu dulu sampai selesai: {item.depends_on_title}{owner}.", status=409)
        photos = None
        if data.photos is not None:
            ids = [str(p.file_id) for p in data.photos]
            if await self.repo.existing_files(ids) != len(set(ids)):
                raise ValidationError("Ada foto yang belum diunggah atau sudah dihapus.")
            photos = [{"file_id": str(p.file_id), "requirement_id": str(p.requirement_id) if p.requirement_id else None}
                      for p in data.photos]
        if data.completed_qty >= item.target_qty:
            given = {str(p["requirement_id"]) for p in (photos if photos is not None else item.realization_photos_json)
                     if p.get("requirement_id")}
            missing = await self.repo.missing_required_photos(item_id, given)
            if missing:
                raise AppError("PHOTOS_REQUIRED", f"Foto wajib belum lengkap: {', '.join(missing)}.", status=422)
        await self.repo.set_progress(item_id, data.completed_qty, item.target_qty, photos,
                                     data.notes.strip() if data.notes else None)
        return await self.repo.get(item_id)

    async def request_rollover(self, user: CurrentUser, item_id: UUID, data: RolloverRequest) -> Any:
        item, access = await self._item(user, item_id, DailyNeed.LEADER)
        require_daily_status(access, *FIELD_ACTIVE)
        if item.status in ("DONE", "SHIFTED_DAY", "PENDING_ROLLOVER"):
            raise _state("Hanya pekerjaan yang belum selesai dan belum diajukan yang bisa dipindah hari.")
        if data.completed_qty >= item.target_qty:
            raise ValidationError("Jumlah selesai sudah mencapai target — tandai selesai, tidak perlu pindah hari.")
        await self.repo.request_rollover(item_id, data.delay_reason.strip(), data.completed_qty)
        return await self.repo.get(item_id)

    async def decide_rollover(self, user: CurrentUser, item_id: UUID, data: RolloverDecision) -> Any:
        item, access = await self._item(user, item_id, DailyNeed.MANAGE)
        locked = await self.repo.lock(item_id)
        if locked is None or locked.rollover_approval_status != "WAITING_PM":
            raise _state("Pekerjaan ini tidak sedang menunggu keputusan pindah hari.")
        log = {"decision": "APPROVED" if data.approve else "REJECTED", "note": (data.note or "").strip() or None,
               "delay_reason": item.delay_reason, "from_daily_plan_id": str(item.daily_plan_id)}
        if not data.approve:
            await self.repo.reject_rollover(item_id, user.employee_id)
            await self.repo.log_decision(user.user_id, user.role, item_id, log)
            return await self.repo.get(item_id)

        origin = access.plan
        if data.target_daily_plan_id:
            target = await self.repo.target_day(data.target_daily_plan_id)
            if target is None:
                raise NotFoundError("Jadwal tujuan")
        else:
            target_date: date = data.target_date  # type: ignore[assignment]  # dijamin validator skema
            target = await self.repo.team_day(origin.team_id, target_date)
        work_date = target.work_date if target else data.target_date
        assert work_date is not None
        if work_date <= origin.work_date:
            raise ValidationError("Tanggal tujuan harus setelah tanggal jadwal asal.")
        if work_date < jakarta_now().date():
            raise ValidationError("Tanggal tujuan tidak boleh lampau.")
        if target is not None:
            if str(target.team_id) != str(origin.team_id) or str(target.division_id) != str(origin.division_id):
                raise ValidationError("Jadwal tujuan harus tim & divisi yang sama (pindah tim = penugasan ulang).")
            if target.status == "COMPLETED":
                raise _state("Jadwal tujuan sudah selesai.")
            target_id = target.daily_plan_id
        else:
            target_id = await self.repo.clone_day(item.daily_plan_id, work_date, user.employee_id)
        new_item = await self.repo.shift(item_id, target_id, user.employee_id)
        log.update(to_daily_plan_id=str(target_id), new_item_id=str(new_item),
                   carried_qty=str(locked.target_qty - locked.completed_qty))
        await self.repo.log_decision(user.user_id, user.role, item_id, log)
        return await self.repo.get(new_item)
