"""
app/modules/work_plans/services/daily_plan_service.py
Jadwal harian daily-first (Milestone 5, docs/35 §3; keputusan pemilik 2026-10-20). Minggu = rentang tanggal.

- Membuat & mengubah: PM/OM divisi (SUPER_ADMIN semua). Tim harus milik divisi itu; satu jadwal per tim per tanggal;
  tanggal tidak boleh lampau, kecuali PM/OM membuat jadwal tanggal lampau <= 7 hari dengan `backdate_reason`
  (tercatat audit BACKDATE_CREATED). Persetujuan tanggal lampau <= 7 hari juga tercatat (BACKDATE_APPROVED).
  Ubah hanya saat DRAFT/SUBMITTED.
- Status: DRAFT → (ajukan) SUBMITTED → (setujui PM) APPROVED → (ketua mulai, pada/after tanggalnya) ONGOING →
  (ketua/PM selesai) COMPLETED. Tolak: SUBMITTED → DRAFT + alasan. PM boleh langsung menyetujui DRAFT
  (persetujuan per hari atau sekaligus satu minggu lewat matriks).
- Lapangan (ketua/anggota) hanya melihat jadwal yang sudah disetujui.
- Hapus (lunak, delete_at): DRAFT/SUBMITTED/APPROVED (belum dimulai) yang belum dipakai absensi/peminjaman aset;
  item ikut terarsip.
"""
from __future__ import annotations

import logging
from datetime import date, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.work_plans.repositories.daily_plan_repository import DailyPlanRepository
from app.modules.work_plans.schemas.daily_plan_schema import (
    DailyActivateIn,
    DailyBulkAsset,
    DailyBulkCellOut,
    DailyBulkIn,
    DailyBulkOut,
    DailyBulkWarning,
    DailyPlanCreate,
    DailyPlanLocationUpdate,
    DailyPlanUpdate,
)
from app.modules.work_plans.services.plan_item_service import PlanItemService
from app.shared.access.access_service import (
    DailyAccess,
    DailyNeed,
    check_daily_access,
    check_division_manager,
    is_admin,
    require_daily_status,
)

logger = logging.getLogger(__name__)

EDITABLE = ("DRAFT", "SUBMITTED")
FIELD_ROLES = ("TEAM_LEADER", "EMPLOYEE")


BACKDATE_DAYS = 7
DELETABLE = ("DRAFT", "SUBMITTED", "APPROVED")  # APPROVED = belum dimulai (ONGOING belum)


def _week(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _backdated(work_date: date, reason: str | None) -> bool:
    """Tanggal lampau: True bila diizinkan (<= BACKDATE_DAYS hari, beralasan). Hari ini/mendatang: False."""
    today = jakarta_now().date()
    if work_date >= today:
        return False
    if work_date < today - timedelta(days=BACKDATE_DAYS):
        raise ValidationError(f"Tanggal jadwal lampau paling jauh {BACKDATE_DAYS} hari dari hari ini.")
    if not (reason and reason.strip()):
        raise ValidationError("Jadwal untuk tanggal lampau wajib disertai alasan (backdate_reason).")
    return True


class DailyPlanService:
    """Use case jadwal harian."""

    def __init__(self, db: AsyncSession, repo: DailyPlanRepository | None = None) -> None:
        self.db = db
        self.repo = repo if repo is not None else DailyPlanRepository(db)

    @staticmethod
    def _manager_scope(user: CurrentUser) -> str | None:
        """employee_id PM/OM yang dibatasi ke divisinya; None = SUPER_ADMIN/HR (semua)."""
        if is_admin(user) or user.has_role("ADMIN_HR_GA"):
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
        field = user.has_role(*FIELD_ROLES)
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

    async def recent_sites(self, user: CurrentUser, team_id: UUID, limit: int) -> list[Any]:
        return await self.repo.recent_sites(team_id=team_id, managed_by=self._manager_scope(user), limit=limit)

    async def form_options(self, user: CurrentUser) -> dict[str, Any]:
        scope = self._manager_scope(user)
        return {
            "divisions": [dict(r._mapping) for r in await self.repo.divisions(scope)],
            "teams": [dict(r._mapping) for r in await self.repo.teams(scope)],
            "orders": [dict(r._mapping) for r in await self.repo.open_orders(scope)],
        }

    async def plans_of_order(self, user: CurrentUser, completion_id: UUID) -> list[Any]:
        """Jadwal yang memuat item order ini. Order tak ada, atau tak boleh dilihat pengguna (bukan pengelola order
        /divisinya dan tak punya jadwal yang terlihat), → 404 seperti detail order."""
        scope = await self.repo.order_scope(completion_id)
        if scope is None:
            raise NotFoundError("Order Proyek Klien")
        rows = await self.repo.plans_of_order(completion_id)
        visible = []
        for row in rows:
            try:
                await check_daily_access(self.db, row.daily_plan_id, user, DailyNeed.VIEW)
                visible.append(row)
            except (NotFoundError, AppError):
                continue
        if not visible and not self._manages_order(user, scope):
            raise NotFoundError("Order Proyek Klien")
        return visible

    async def order_target_totals(self, completion_id: UUID) -> Any:
        """Total target order, yang sudah selesai, dan yang sudah masuk jadwal (dipanggil setelah akses dicek)."""
        totals = await self.repo.order_target_totals(completion_id)
        if totals is None:
            raise NotFoundError("Order Proyek Klien")
        return totals

    @staticmethod
    def _manages_order(user: CurrentUser, scope: Any) -> bool:
        """Super Admin, HR/GA, PM order, atau PM/OM divisi order."""
        if is_admin(user) or user.has_role("ADMIN_HR_GA"):
            return True
        emp = user.employee_id
        return bool(emp) and emp in {str(scope.pm_id), str(scope.div_pm_id), str(scope.div_om_id)}

    # ── Tulis ─────────────────────────────────────────────────────────────────
    async def _check_team_day(self, division_id: UUID, team_id: UUID, work_date: date, exclude: UUID | None,
                              *, allow_past: bool = False) -> None:
        if not await self.repo.team_of_division(team_id, division_id):
            raise ValidationError("Tim tidak ditemukan, nonaktif, atau bukan milik divisi ini.")
        if work_date < jakarta_now().date() and not allow_past:
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
            # Peringatan saja (docs alur: batas tanggal project jadi peringatan, bukan penolakan)
            logger.warning(
                "Jadwal harian dibuat di luar rentang tanggal proyek %s (%s s.d %s) untuk tanggal %s",
                project_id,
                project.start_date,
                project.end_date,
                work_date,
            )

    async def create(self, user: CurrentUser, data: DailyPlanCreate) -> Any:
        await check_division_manager(self.db, data.division_id, user)
        backdated = _backdated(data.work_date, data.backdate_reason)
        await self._check_team_day(data.division_id, data.team_id, data.work_date, None, allow_past=backdated)
        await self._check_project(data.project_id, data.division_id, data.work_date)
        if not user.employee_id:
            raise ValidationError("Akun ini belum terhubung ke data karyawan; jadwal butuh pembuat yang tercatat.")
        fields = data.model_dump()
        reason = fields.pop("backdate_reason", None)
        fields.update(division_id=str(data.division_id), team_id=str(data.team_id), created_by_id=user.employee_id,
                      site_name=data.site_name.strip() if data.site_name else None,
                      project_id=str(data.project_id) if data.project_id else None)
        new_id = await self.repo.insert(fields)
        if backdated:
            await self.repo.log_audit(user.user_id, user.role or "", new_id, "BACKDATE_CREATED",
                                      {"work_date": str(data.work_date), "reason": reason.strip()})
        return await self.repo.get(new_id)

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
        site_lat = data.site_lat if "site_lat" in data.model_fields_set else current.site_lat
        site_lng = data.site_lng if "site_lng" in data.model_fields_set else current.site_lng
        if (site_lat is None) != (site_lng is None):
            raise ValidationError("Latitude dan longitude harus diisi bersama atau dibiarkan kosong.")
        clock_in = data.clock_in_time or current.clock_in_time
        clock_out = data.clock_out_time or current.clock_out_time
        if clock_out <= clock_in:
            raise ValidationError("Jam pulang harus setelah jam masuk.")
        fields = data.model_dump()
        fields.update(
            site_name_set="site_name" in data.model_fields_set,
            site_lat_set="site_lat" in data.model_fields_set,
            site_lng_set="site_lng" in data.model_fields_set,
            attendance_radius_m_set="attendance_radius_m" in data.model_fields_set,
        )
        fields.update(team_id=str(data.team_id) if data.team_id else None,
                      project_id=str(data.project_id) if data.project_id else None,
                      site_name=data.site_name.strip() if data.site_name else None)
        await self.repo.update(daily_plan_id, fields)
        return await self.repo.get(daily_plan_id)

    async def update_location(self, user: CurrentUser, daily_plan_id: UUID, data: DailyPlanLocationUpdate) -> Any:
        """Ubah lokasi (nama, koordinat, radius) jadwal DISETUJUI yang belum dimulai, tanpa mengembalikan ke draf.
        Dicatat di audit LOCATION_CHANGED dengan nilai sebelum dan sesudah."""
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, "APPROVED")
        plan = access.plan
        if plan.work_date <= jakarta_now().date():
            raise AppError("PLAN_STARTED", "Lokasi hanya dapat diubah sebelum hari kerja dimulai.", status=409)
        current = await self.repo.get(daily_plan_id)
        name = data.site_name.strip()
        await self.repo.update(daily_plan_id, {
            "team_id": None, "project_id": None, "work_date": None, "clock_in_time": None, "clock_out_time": None,
            "site_name": name, "site_name_set": True,
            "site_lat": data.site_lat, "site_lat_set": True,
            "site_lng": data.site_lng, "site_lng_set": True,
            "attendance_radius_m": data.attendance_radius_m, "attendance_radius_m_set": True,
        })
        await self.repo.log_audit(user.user_id, user.role or "", daily_plan_id, "LOCATION_CHANGED", {
            "from": {"site_name": current.site_name, "site_lat": str(current.site_lat),
                     "site_lng": str(current.site_lng), "attendance_radius_m": current.attendance_radius_m},
            "to": {"site_name": name, "site_lat": str(data.site_lat), "site_lng": str(data.site_lng),
                   "attendance_radius_m": data.attendance_radius_m},
        })
        return await self.repo.get(daily_plan_id)

    async def copy(self, user: CurrentUser, daily_plan_id: UUID, work_dates: list[date]) -> list[Any]:
        """Salin lokasi, jam, tim, dan item ke tanggal lain sebagai DRAFT. Progres item direset; item survei dan item
        yang bergantung pada prasyarat tidak disalin (lihat `DailyPlanRepository.copy_items`)."""
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        source = await self.repo.get(daily_plan_id)
        created = []
        for work_date in sorted(set(work_dates)):
            await self._check_team_day(access.plan.division_id, source.team_id, work_date, None)
            await self._check_project(source.project_id, source.division_id, work_date)
            fields = {k: getattr(source, k) for k in ("work_date", "site_name", "site_lat", "site_lng",
                                                      "attendance_radius_m", "clock_in_time", "clock_out_time",
                                                      "kind")}
            fields.update(work_date=work_date, division_id=str(source.division_id), team_id=str(source.team_id),
                          created_by_id=user.employee_id,
                          project_id=str(source.project_id) if source.project_id else None)
            new_id = await self.repo.insert(fields)
            await self.repo.copy_items(daily_plan_id, new_id)
            created.append(await self.repo.get(new_id))
        return created

    async def delete(self, user: CurrentUser, daily_plan_id: UUID) -> None:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, *DELETABLE)
        if await self.repo.has_activity(daily_plan_id):
            raise AppError("DAILY_PLAN_IN_USE", "Jadwal sudah dipakai absensi atau peminjaman aset.", status=409)
        await self.repo.archive(daily_plan_id)

    async def set_attachments(self, user: CurrentUser, daily_plan_id: UUID, file_ids: list[UUID]) -> list[UUID]:
        await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        if await self.repo.existing_files(file_ids) != len(set(file_ids)):
            raise ValidationError("Ada berkas lampiran yang belum diunggah atau sudah dihapus.")
        await self.repo.replace_attachments(daily_plan_id, file_ids)
        return await self.repo.attachment_ids(daily_plan_id)

    # ── Alokasi massal & siaga ─────────────────────────────────────────────────
    async def _bulk_cell_problem(self, data: DailyBulkIn, team_id: UUID, work_date: date) -> tuple[str, str] | None:
        """Alasan sel dilewati (kode, pesan) atau None bila sel bisa dibuat. Tidak melempar galat per sel."""
        if not await self.repo.team_of_division(team_id, data.division_id):
            return "TEAM_BUKAN_DIVISI", "Tim tidak ditemukan, nonaktif, atau bukan milik divisi ini."
        if work_date < jakarta_now().date():
            return "TANGGAL_LAMPAU", "Tanggal sudah lewat; alokasi hanya untuk hari ini atau mendatang."
        if await self.repo.team_day_taken(team_id, work_date):
            return "TEAM_DAY_TAKEN", "Tim ini sudah punya jadwal pada tanggal tersebut."
        return None

    async def bulk_create(self, user: CurrentUser, data: DailyBulkIn) -> DailyBulkOut:
        """Membuat jadwal untuk setiap pasangan (tim, tanggal) dalam satu transaksi permintaan.

        Sel yang tidak memenuhi aturan dilaporkan sebagai SKIPPED dan tidak menggagalkan sel lain. Seluruh sel
        ditulis dalam satu sesi, jadi galat tak terduga di tengah jalan membatalkan permintaan secara utuh."""
        await check_division_manager(self.db, data.division_id, user)
        if not user.employee_id:
            raise ValidationError("Akun ini belum terhubung ke data karyawan; jadwal butuh pembuat yang tercatat.")
        cells: list[DailyBulkCellOut] = []
        leaders = {team_id: await self.repo.team_leader(team_id) for team_id in dict.fromkeys(data.team_ids)}
        for team_id in dict.fromkeys(data.team_ids):
            for work_date in sorted(set(data.work_dates)):
                problem = await self._bulk_cell_problem(data, team_id, work_date)
                if problem:
                    cells.append(DailyBulkCellOut(team_id=team_id, work_date=work_date, status="SKIPPED",
                                                  reason=problem[0], message=problem[1]))
                    continue
                # Peringatan hanya memberi tahu; sel tetap dibuat.
                warnings = await self._cell_warnings(leaders.get(team_id), work_date, data.assets)
                new_id = await self.repo.insert({
                    "division_id": str(data.division_id), "team_id": str(team_id), "project_id": None,
                    "work_date": work_date, "site_name": data.site_name.strip() if data.site_name else None,
                    "site_lat": data.site_lat, "site_lng": data.site_lng,
                    "attendance_radius_m": data.attendance_radius_m, "clock_in_time": time(7, 0),
                    "clock_out_time": time(16, 0), "kind": data.kind, "created_by_id": user.employee_id,
                })
                if data.target == "APPROVED":
                    await self.repo.set_status(new_id, "APPROVED", approver=user.employee_id)
                cells.append(DailyBulkCellOut(team_id=team_id, work_date=work_date, status="CREATED",
                                              daily_plan_id=new_id, warnings=warnings))
        created = sum(1 for c in cells if c.status == "CREATED")
        return DailyBulkOut(created=created, skipped=len(cells) - created, cells=cells)

    async def _cell_warnings(self, leader_id: str | None, work_date: date,
                             assets: list[DailyBulkAsset]) -> list[DailyBulkWarning]:
        """Peringatan satu sel: ketua cuti pada tanggal itu; aset yang dipinjam pada tanggal itu (atau tanpa jadwal)."""
        warnings: list[DailyBulkWarning] = []
        if leader_id and await self.repo.leader_on_leave(leader_id, work_date):
            warnings.append(DailyBulkWarning(code="LEADER_CUTI", message="Ketua tim sedang cuti pada tanggal ini."))
        for asset in assets:
            loan = await self.repo.asset_loan_conflict(asset.asset_type, asset.asset_id, work_date)
            if loan is not None:
                holder = f"tim {loan.team_name}" if loan.team_name else "peminjaman tanpa jadwal"
                warnings.append(DailyBulkWarning(code="ASET_BENTROK",
                                                 message=f"Aset sedang dipinjam ({holder}) pada tanggal ini."))
        return warnings

    # ── Matriks mingguan ───────────────────────────────────────────────────────
    async def weekly_matrix(self, user: CurrentUser, week_start: date, division_id: UUID | None) -> dict[str, Any]:
        """Tim (baris) × 7 hari Senin–Minggu (kolom) untuk divisi yang dikelola pengguna. `division_id` opsional
        (None = semua divisi PM/OM; SUPER_ADMIN/HR semua divisi). Satu tim paling banyak satu jadwal per tanggal."""
        if week_start.weekday() != 0:
            raise ValidationError("Awal minggu (week_start) harus hari Senin.")
        scope = self._manager_scope(user)
        divisions = [dict(r._mapping) for r in await self.repo.divisions(scope)]
        if division_id is not None and str(division_id) not in {str(d["division_id"]) for d in divisions}:
            raise NotFoundError("Divisi")
        days = [week_start + timedelta(days=i) for i in range(7)]
        plans = await self.repo.list_plans(start=days[0], end=days[-1], division_id=division_id, team_id=None,
                                           status=None, managed_by=scope, field_employee=None)
        plan_by_cell = {(str(p.team_id), p.work_date): p for p in plans}
        items_by_plan: dict[str, list[dict[str, Any]]] = {}
        completion_ids: list[str] = []
        for row in await self.repo.weekly_items([str(p.daily_plan_id) for p in plans]):
            item = dict(row._mapping)
            items_by_plan.setdefault(str(item["daily_plan_id"]), []).append(item)
            if item["completion_id"] and str(item["completion_id"]) not in completion_ids:
                completion_ids.append(str(item["completion_id"]))
        orders = {str(o.completion_id): dict(o._mapping) for o in await self.repo.orders_brief(completion_ids)}
        division_names = {str(d["division_id"]): d["name"] for d in divisions}

        rows = []
        for team in await self.repo.teams(scope, division_id):
            cells = []
            for day in days:
                cell: dict[str, Any] = {"work_date": day}
                plan = plan_by_cell.get((str(team.team_id), day))
                if plan is not None:
                    items = items_by_plan.get(str(plan.daily_plan_id), [])
                    cell_orders: list[dict[str, Any]] = []
                    for cid in dict.fromkeys(str(i["completion_id"]) for i in items if i["completion_id"]):
                        order = orders.get(cid)
                        if order is None:
                            continue
                        total = order["total_target_unit"] or 0
                        cell_orders.append({
                            "completion_id": cid, "client_name": order["client_name"],
                            "project_title": order["project_title"], "order_number": order["order_number"],
                            "total_target_unit": total,
                            "remaining_qty": max(total - order["completed_target_unit"], 0),
                            "unscheduled_qty": max(total - (order["scheduled_qty"] or 0), 0),
                        })
                    cell.update(daily_plan_id=plan.daily_plan_id, status=plan.status, kind=plan.kind,
                                item_count=plan.item_count, items=items[:20], orders=cell_orders)
                cells.append(cell)
            rows.append({"team_id": team.team_id, "team_name": team.name, "division_id": team.division_id,
                         "division_name": division_names.get(str(team.division_id), ""),
                         "leader_name": team.leader_name, "cells": cells})
        return {"week_start": days[0], "week_end": days[-1], "days": days,
                "divisions": [{"division_id": d["division_id"], "name": d["name"]} for d in divisions],
                "rows": rows}

    async def bulk_standby_empty_days(self, user: CurrentUser, team_ids: list[UUID], work_dates: list[date],
                                      division_id: UUID) -> DailyBulkOut:
        """Tandai hari kosong tim sebagai siaga (disetujui). Hanya sel tanpa jadwal yang dibuat."""
        data = DailyBulkIn(division_id=division_id, team_ids=team_ids, work_dates=work_dates, kind="STANDBY",
                           target="APPROVED")
        return await self.bulk_create(user, data)

    async def activate(self, user: CurrentUser, daily_plan_id: UUID, data: DailyActivateIn) -> Any:
        """Ubah jadwal siaga menjadi pekerjaan klien: tambah item, ubah kind jadi WORK, beri tahu ketua & anggota."""
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        if access.plan.kind != "STANDBY":
            raise AppError("BUKAN_SIAGA", "Hanya jadwal siaga yang dapat diubah jadi pekerjaan.", status=409)
        require_daily_status(access, "DRAFT", "SUBMITTED", "APPROVED")
        items = PlanItemService(self.db)
        for item in data.items:
            await items.add_validated(access, daily_plan_id, item)
        await self.repo.set_kind(daily_plan_id, "WORK")
        people = await NotificationService(self.db).repo.daily_people(daily_plan_id)
        if people:
            await NotificationService(self.db).notify_employees(
                [people.leader, *people.members], "DAILY_ACTIVATED",
                f"Tim Anda mendapat tugas {NotificationService._day_label(people)}", people.site_name or "",
                target="plan", plan_id=daily_plan_id,
            )
        return await self.repo.get(daily_plan_id)

    # ── Status ────────────────────────────────────────────────────────────────
    async def _require_items_unless_standby(self, access: DailyAccess, daily_plan_id: UUID | str) -> None:
        """Jadwal STANDBY (tim siaga) boleh diajukan/disetujui tanpa item; jadwal WORK wajib berisi pekerjaan."""
        if access.plan.kind == "STANDBY":
            return
        await self._require_items(daily_plan_id)

    async def _require_items(self, daily_plan_id: UUID | str) -> None:
        if await self.repo.count_items(daily_plan_id) == 0:
            raise AppError("PLAN_EMPTY", "Jadwal belum berisi pekerjaan; tambahkan item sebelum diajukan.", status=422)

    async def submit(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, "DRAFT")
        await self._require_items_unless_standby(access, daily_plan_id)
        await self.repo.set_status(daily_plan_id, "SUBMITTED")
        await NotificationService(self.db).daily_submitted(daily_plan_id)
        return await self.repo.get(daily_plan_id)

    async def approve(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.MANAGE)
        require_daily_status(access, *EDITABLE)
        work_date = access.plan.work_date
        today = jakarta_now().date()
        if work_date < today - timedelta(days=BACKDATE_DAYS):
            raise ValidationError(f"Jadwal lebih dari {BACKDATE_DAYS} hari yang lalu tidak dapat disetujui.")
        await self._require_items_unless_standby(access, daily_plan_id)
        one_step = access.plan.status == "DRAFT"
        if one_step:
            # PM/OM menyetujui draf miliknya dalam satu langkah (submit+approve atomik); jejak keduanya dicatat.
            await self.repo.log_audit(user.user_id, user.role or "", daily_plan_id, "SUBMITTED",
                                      {"via": "ONE_STEP_APPROVE"})
        await self.repo.set_status(daily_plan_id, "APPROVED", approver=user.employee_id)
        if one_step:
            await self.repo.log_audit(user.user_id, user.role or "", daily_plan_id, "APPROVED",
                                      {"via": "ONE_STEP_APPROVE", "from": "DRAFT"})
        if work_date < today:
            await self.repo.log_audit(user.user_id, user.role or "", daily_plan_id, "BACKDATE_APPROVED",
                                      {"work_date": str(work_date)})
        await NotificationService(self.db).daily_approved(daily_plan_id)
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
        await NotificationService(self.db).daily_rejected(daily_plan_id, reason.strip())
        return await self.repo.get(daily_plan_id)

    async def start(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.LEADER)
        require_daily_status(access, "APPROVED")
        if access.plan.work_date > jakarta_now().date():
            raise ValidationError("Jadwal baru bisa dimulai pada tanggalnya.")
        if not await self.repo.leader_checked_in(daily_plan_id, jakarta_now().date()):
            raise AppError(
                "CHECKIN_REQUIRED",
                "Ketua tim harus absen masuk hari ini sebelum jadwal dimulai.",
                status=409,
            )
        await self.repo.set_status(daily_plan_id, "ONGOING")
        return await self.repo.get(daily_plan_id)

    async def complete(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        access = await self.access(user, daily_plan_id, DailyNeed.VIEW)
        if not (access.is_leader or access.manages):
            raise AppError("FORBIDDEN", "Hanya ketua tim atau PM/OM divisi yang dapat menutup jadwal.", status=403)
        require_daily_status(access, "ONGOING")
        if await self.repo.has_open_correction(daily_plan_id):
            raise AppError(
                "CORRECTION_OPEN",
                "Ada koreksi laporan yang belum selesai; kirim koreksinya, bukan menutup jadwal langsung.",
                status=409,
            )
        if await self.repo.has_pending_rollover(daily_plan_id):
            raise AppError(
                "ROLLOVER_PENDING",
                "Ada pekerjaan yang menunggu keputusan pemindahan hari; selesaikan keputusannya dulu.",
                status=409,
            )
        if not await self.repo.has_daily_report(daily_plan_id):
            raise AppError(
                "REPORT_REQUIRED",
                "Laporan harian ketua tim wajib diisi sebelum jadwal dapat diselesaikan.",
                status=422,
            )
        await self.repo.set_status(daily_plan_id, "COMPLETED")
        await self.repo.release_plan_assets(daily_plan_id)
        return await self.repo.get(daily_plan_id)

    async def submit_daily_report(self, user: CurrentUser, daily_plan_id: UUID, data: Any) -> Any:
        """Kirim atau perbarui laporan harian ketua tim untuk jadwal ini."""
        access = await self.access(user, daily_plan_id, DailyNeed.VIEW)
        if not (access.is_leader or access.manages):
            raise AppError(
                "FORBIDDEN",
                "Hanya ketua tim atau PM/OM divisi yang dapat mengisi laporan harian.",
                status=403,
            )
        require_daily_status(access, "APPROVED", "ONGOING", "COMPLETED")
        leader_id = user.employee_id if access.is_leader else access.plan.leader_employee_id
        if not leader_id:
            raise ValidationError("Ketua tim tidak ditemukan pada jadwal ini.")
        photos = data.photos_json if hasattr(data, "photos_json") else data.get("photos_json", [])
        summary = data.summary if hasattr(data, "summary") else data.get("summary", "")
        obstacles = data.obstacles if hasattr(data, "obstacles") else data.get("obstacles")
        await self.repo.create_daily_report(daily_plan_id, leader_id, summary, obstacles, photos)
        notifier = NotificationService(self.db)
        people = await notifier.repo.daily_people(daily_plan_id)
        if people:
            await notifier.notify_employees(
                [people.pm, people.om], "DAILY_REPORT_SUBMITTED",
                f"Laporan harian {people.team_name} dikirim", people.site_name or "",
                target="plan", plan_id=daily_plan_id,
            )
        return await self.repo.get_daily_report(daily_plan_id)

    async def get_daily_report(self, user: CurrentUser, daily_plan_id: UUID) -> Any:
        """Mengambil data laporan harian jadwal kerja."""
        await self.access(user, daily_plan_id, DailyNeed.VIEW)
        report = await self.repo.get_daily_report(daily_plan_id)
        if not report:
            raise NotFoundError("Laporan harian")
        return report

    async def get_weekly_presentation(
        self, user: CurrentUser, team_id: UUID, meeting_date: date
    ) -> dict[str, Any]:
        """Rekapitulasi laporan harian tim selama satu minggu (Senin - Sabtu) untuk meeting evaluasi mingguan."""
        start_date = meeting_date - timedelta(days=5)
        reports = await self.repo.get_weekly_reports_for_team(team_id, start_date, meeting_date)
        team = await self.repo.team_standing(team_id)
        team_name = team.name if team else "Tim Lapangan"
        completed = sum(1 for r in reports if getattr(r, "plan_status", None) == "COMPLETED")
        return {
            "team_id": team_id,
            "team_name": team_name,
            "week_start": start_date.strftime("%Y-%m-%d"),
            "week_end": meeting_date.strftime("%Y-%m-%d"),
            "total_plans": len(reports),
            "completed_plans": completed,
            "daily_reports": reports,
            "presentation_notes": f"Meeting evaluasi mingguan tim {team_name} periode {start_date} s/d {meeting_date}.",
            "pm_feedback": "Seluruh laporan harian telah ditinjau dan dievaluasi bersama PM & Team Leader.",
        }

