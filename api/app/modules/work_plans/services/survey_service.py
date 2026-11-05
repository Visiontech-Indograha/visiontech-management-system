"""
app/modules/work_plans/services/survey_service.py
Survei ACS & CCTV berformat baku (docs/37):
- PM: tugas survei = item fase SURVEY yang menempel pada order (laporan) di jadwal yang diterbitkan.
- Ketua tim (jadwal berjalan): menambah titik — foto per slot (image_requirement), remark, baris MATERIAL /
  KEBUTUHAN / KABEL — serta narasi, tujuan, dan lokasi laporan (layout otomatis dari koordinat titik); lalu KIRIM.
- PM/OM divisi: SETUJUI (BoM = jumlah MATERIAL) atau KEMBALIKAN dengan catatan; setelah disetujui
  "rencanakan dari survei" membuat item lanjutan per titik pada jadwal DRAFT/SUBMITTED tim yang sama.
Format laporan mengikuti divisi: divisi ACS → format ACS, selain itu format CCTV.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.work_plans.repositories.survey_repository import SurveyRepository
from app.modules.work_plans.schemas.survey_schema import (
    CatalogAddIn,
    LineEditIn,
    PlanFromSurveyIn,
    PointIn,
    PointLine,
    PointLocationIn,
    ReportIn,
    ReviewIn,
)
from app.shared.access.access_service import DailyAccess, DailyNeed, check_daily_access, is_admin

FIELD_OPEN = ("APPROVED", "ONGOING")
PLANNABLE = ("DRAFT", "SUBMITTED")
GENERAL_GROUP = "Umum"  # material umum lokasi (baris BoM milik tugas survei)


def survey_format(division_name: str) -> str:
    name = division_name.upper()
    return "ACS" if "ACS" in name or "ACCESS CONTROL" in name else "CCTV"


def survey_state(task: Any) -> str:
    if task.approved_by_pm_id:
        return "APPROVED"
    return "SUBMITTED" if task.status == "DONE" else "DRAFT"


def _state(message: str) -> AppError:
    return AppError("INVALID_STATE", message, status=409)


class SurveyService:
    """Use case survei per titik."""

    def __init__(self, db: AsyncSession, repo: SurveyRepository | None = None) -> None:
        self.db = db
        self.repo = repo if repo is not None else SurveyRepository(db)

    async def create_revision_task(self, data: dict[str, Any]) -> UUID | None:
        """Membuat tugas survei revisi."""
        return await self.repo.create_task(data)

    async def _task(self, user: CurrentUser, task_id: UUID, need: DailyNeed) -> tuple[Any, DailyAccess]:
        task = await self.repo.task(task_id)
        if task is None or task.task_phase != "SURVEY" or task.depends_on_item_id is not None:
            raise NotFoundError("Tugas survei")
        if task.completion_id is None:
            raise ValidationError("Tugas survei belum dikaitkan ke order laporan — minta PM mengaitkannya.")
        access = await check_daily_access(self.db, task.daily_plan_id, user, need)
        return task, access

    async def _editable_task(self, user: CurrentUser, task_id: UUID) -> Any:
        task, access = await self._task(user, task_id, DailyNeed.LEADER)
        if access.plan.status not in FIELD_OPEN:
            raise _state("Survei hanya bisa diisi saat jadwal sudah terbit/berjalan.")
        if survey_state(task) != "DRAFT":
            raise _state("Survei sudah dikirim — tunggu keputusan PM.")
        return task

    # ── Baca ──────────────────────────────────────────────────────────────────
    async def _type_entry(self, work_type_id: Any, name: str, follow_up: Any) -> dict[str, Any]:
        return {
            "work_type_id": work_type_id, "name": name, "follow_up_work_type_id": follow_up,
            "slots": [dict(x._mapping) for x in await self.repo.slots(work_type_id)],
            "catalog": [dict(x._mapping) for x in await self.repo.catalog(work_type_id)],
        }

    async def _point_types(self, task: Any) -> list[dict[str, Any]]:
        """Jenis titik divisi (SURVEY_POINT) + slot & katalognya. Divisi tanpa jenis titik → jenis bawaan = work
        type tugas survei itu sendiri (perilaku lama)."""
        rows = await self.repo.point_types(task.division_id)
        types = [(r.work_type_id, r.name, r.follow_up_work_type_id) for r in rows] or [
            (task.work_type_id, task.work_type_name, None)]
        return [await self._type_entry(wt, name, follow_up) for wt, name, follow_up in types]

    async def detail(self, user: CurrentUser, task_id: UUID) -> dict[str, Any]:
        task, access = await self._task(user, task_id, DailyNeed.VIEW)
        types = await self._point_types(task)
        by_type = {str(t["work_type_id"]): t for t in types}
        points = await self.repo.points(task_id)
        if any(str(p.work_type_id) not in by_type for p in points):
            # Titik lama (dibuat sebelum ada jenis titik) tetap memakai slot & katalog work type tugas survei.
            by_type[str(task.work_type_id)] = await self._type_entry(task.work_type_id, task.work_type_name, None)
        # Termasuk slot lama yang diarsipkan; satu kueri untuk seluruh jenis pekerjaan.
        slot_name = await self.repo.slot_names(sorted({str(p.work_type_id) for p in points} | set(by_type)
                                                      | {str(task.work_type_id)}))
        lines = await self.repo.lines([str(p.point_id) for p in points] + [str(task.item_id)])
        by_item: dict[str, list[Any]] = {}
        for line in lines:
            by_item.setdefault(str(line.point_id), []).append(line)

        def out_line(ln: Any, catalog: set[str]) -> dict[str, Any]:
            return {**dict(ln._mapping), "custom": ln.category == "MATERIAL" and ln.name.strip().lower() not in catalog}

        bom: OrderedDict[tuple[str, str, str], dict[str, Any]] = OrderedDict()

        def add_bom(group: str, ln: dict[str, Any]) -> None:
            row = bom.setdefault((group, ln["name"], ln["unit"]), {
                "group": group, "name": ln["name"], "unit": ln["unit"], "qty": Decimal(0), "custom": ln["custom"]})
            row["qty"] += Decimal(ln["qty"])

        out_points = []
        for p in points:
            ptype = by_type.get(str(p.work_type_id)) or by_type[str(task.work_type_id)]
            catalog = {c["name"].strip().lower() for c in ptype["catalog"]}
            plines = [out_line(ln, catalog) for ln in by_item.get(str(p.point_id), [])]
            for ln in plines:
                if ln["category"] == "MATERIAL":
                    add_bom(ptype["name"], ln)
            out_points.append({
                "point_id": p.point_id, "name": p.name,
                "point_type_id": ptype["work_type_id"], "point_type_name": ptype["name"],
                "point_status": p.point_status,
                "remarks": [r for r in (p.notes or "").split("\n") if r.strip()],
                "photos": [{"file_id": ph.get("file_id"), "requirement_id": ph.get("requirement_id"),
                            "slot": slot_name.get(str(ph.get("requirement_id")))}
                           for ph in (p.photos or []) if isinstance(ph, dict) and ph.get("file_id")],
                "lines": plines,
                "site_lat": p.site_lat, "site_lng": p.site_lng, "update_at": p.update_at,
            })
        all_catalog = {c["name"].strip().lower() for t in types for c in t["catalog"]}
        general = [out_line(ln, all_catalog) for ln in by_item.get(str(task.item_id), [])]
        for ln in general:
            add_bom(GENERAL_GROUP, ln)
        state = survey_state(task)
        can_edit = access.is_leader and state == "DRAFT" and task.plan_status in FIELD_OPEN
        return {
            "task_id": task.item_id, "daily_plan_id": task.daily_plan_id, "work_date": task.work_date,
            "plan_status": task.plan_status, "team_id": task.team_id, "team_name": task.team_name,
            "division_id": task.division_id,
            "division_name": task.division_name, "format": survey_format(task.division_name),
            "work_type_id": task.work_type_id, "work_type_name": task.work_type_name,
            "completion_id": task.completion_id, "client_name": task.client_name, "project_title": task.project_title,
            "location": task.site_address, "purpose": task.project_title, "narrative": task.summary_notes or None,
            "state": state,
            "review_note": await self.repo.review_note(task_id),
            "point_types": types,
            "points": out_points,
            "general_lines": general,
            "bom": list(bom.values()),
            "can_edit": can_edit,
            "can_review": access.manages and state == "SUBMITTED",
            "can_edit_bom": can_edit or (access.manages and state == "SUBMITTED"),
            # Geser titik di peta layout: PM kapan pun, ketua tim selama masih bisa mengisi.
            "can_move": access.manages or can_edit,
        }

    async def list_surveys(self, user: CurrentUser, state: str | None) -> list[dict[str, Any]]:
        """Daftar survei: admin & OM semua; PM/OM divisi yang dipimpin; ketua/anggota tim sendiri (jadwal terbit)."""
        sees_all = is_admin(user) or user.has_role("OPERATIONAL_MANAGER")
        if not sees_all and not user.employee_id:
            return []
        rows = await self.repo.list_tasks(user.employee_id, sees_all, state)
        return [{**dict(r._mapping), "format": survey_format(r.division_name)} for r in rows]

    # ── Ketua tim ─────────────────────────────────────────────────────────────
    async def _point_payload(self, task: Any, data: PointIn) -> dict[str, Any]:
        types = await self._point_types(task)
        if data.point_type_id is None:
            ptype: dict[str, Any] | None = types[0]
        else:
            ptype = next((t for t in types if str(t["work_type_id"]) == str(data.point_type_id)), None)
        if ptype is None:
            raise ValidationError("Jenis titik tidak tersedia untuk survei divisi ini.")
        slots = {str(s["requirement_id"]) for s in ptype["slots"]}
        if any(str(p.requirement_id) not in slots for p in data.photos):
            raise ValidationError(f"Slot foto tidak sesuai jenis titik '{ptype['name']}'.")
        ids = [str(p.file_id) for p in data.photos]
        if ids and await self.repo.existing_files(ids) != len(set(ids)):
            raise ValidationError("Ada foto yang belum diunggah atau sudah dihapus.")
        return {
            "name": data.name.strip(), "notes": "\n".join(data.remarks) or None,
            "photos": json.dumps([{"file_id": str(p.file_id), "requirement_id": str(p.requirement_id)}
                                  for p in data.photos]),
            "lat": data.site_lat, "lng": data.site_lng,
            "wt": str(ptype["work_type_id"]), "status": data.point_status,
        }

    @staticmethod
    def _lines(data: PointIn) -> list[dict[str, Any]]:
        return [{"category": ln.category, "name": ln.name.strip(), "qty": ln.qty, "unit": ln.unit.strip(),
                 "notes": (ln.notes or "").strip() or None} for ln in data.lines]

    async def add_point(self, user: CurrentUser, task_id: UUID, data: PointIn) -> dict[str, Any]:
        task = await self._editable_task(user, task_id)
        point_id = await self.repo.insert_point(task, await self._point_payload(task, data))
        await self.repo.replace_lines(task.completion_id, point_id, self._lines(data))
        return await self.detail(user, task_id)

    async def update_point(self, user: CurrentUser, point_id: UUID, data: PointIn) -> dict[str, Any]:
        point = await self.repo.point(point_id)
        if point is None:
            raise NotFoundError("Titik survei")
        task = await self._editable_task(user, point.task_id)
        await self.repo.update_point(point_id, await self._point_payload(task, data))
        await self.repo.replace_lines(task.completion_id, point_id, self._lines(data))
        return await self.detail(user, point.task_id)

    async def move_point(self, user: CurrentUser, point_id: UUID, data: PointLocationIn) -> dict[str, Any]:
        """Sesuaikan koordinat titik dari peta layout (dipakai layout otomatis laporan)."""
        point = await self.repo.point(point_id)
        if point is None:
            raise NotFoundError("Titik survei")
        _, access = await self._task(user, point.task_id, DailyNeed.VIEW)
        if not access.manages:
            await self._editable_task(user, point.task_id)
        await self.repo.set_point_location(point_id, data.site_lat, data.site_lng)
        return await self.detail(user, point.task_id)

    async def delete_point(self, user: CurrentUser, point_id: UUID) -> dict[str, Any]:
        point = await self.repo.point(point_id)
        if point is None:
            raise NotFoundError("Titik survei")
        await self._editable_task(user, point.task_id)
        await self.repo.archive_point(point_id)
        return await self.detail(user, point.task_id)

    async def save_report(self, user: CurrentUser, task_id: UUID, data: ReportIn) -> dict[str, Any]:
        task = await self._editable_task(user, task_id)
        await self.repo.save_report(task.completion_id, {
            "narrative": (data.narrative or "").strip() or None,
            "purpose": (data.purpose or "").strip() or None,
            "location": (data.location or "").strip() or None,
        })
        return await self.detail(user, task_id)

    async def submit(self, user: CurrentUser, task_id: UUID) -> dict[str, Any]:
        task = await self._editable_task(user, task_id)
        survey = await self.detail(user, task_id)
        if not survey["points"]:
            raise ValidationError("Tambahkan minimal satu titik survei sebelum dikirim.")
        slots = {str(t["work_type_id"]): t["slots"] for t in survey["point_types"]}
        for p in survey["points"]:
            if not p["photos"]:
                raise ValidationError(f"Titik '{p['name']}' belum punya foto.")
            given = {(ph.get("slot") or "").strip().lower() for ph in p["photos"]}  # dicocokkan per nama slot
            mandatory = [s for s in slots.get(str(p["point_type_id"]), []) if s["mandatory"]]
            missing = [s["name"] for s in mandatory if s["name"].strip().lower() not in given]
            if missing:
                raise AppError("PHOTOS_REQUIRED", f"Titik '{p['name']}': foto wajib belum lengkap — "
                                                  f"{', '.join(missing)}.", status=422)
        await self.repo.set_task_state(task.item_id, done=True, approver=None)
        await self.repo.log(user.user_id, user.role or "", task_id, "SURVEY_SUBMITTED",
                            {"points": len(survey["points"])})
        return await self.detail(user, task_id)

    # ── BoM: ketua tim saat draf, PM saat meninjau ────────────────────────────
    async def _bom_task(self, user: CurrentUser, task_id: UUID) -> Any:
        task, access = await self._task(user, task_id, DailyNeed.VIEW)
        state = survey_state(task)
        if access.manages and state == "SUBMITTED":
            return task
        if access.is_leader and state == "DRAFT" and task.plan_status in FIELD_OPEN:
            return task
        raise _state("Daftar material hanya bisa diubah ketua tim sebelum survei dikirim, atau PM saat memeriksa.")

    async def _bom_log(self, user: CurrentUser, task_id: UUID, change: str, diff: dict[str, Any]) -> None:
        await self.repo.log(user.user_id, user.role or "", task_id, "SURVEY_BOM_CHANGED", {"change": change, **diff})

    async def add_general_line(self, user: CurrentUser, task_id: UUID, data: PointLine) -> dict[str, Any]:
        """Material umum lokasi (bukan milik satu titik): rack, panel, kabel tray utama, …"""
        task = await self._bom_task(user, task_id)
        line = {"category": "MATERIAL", "name": data.name.strip(), "qty": data.qty, "unit": data.unit.strip(),
                "notes": (data.notes or "").strip() or None}
        await self.repo.insert_line(task.completion_id, task.item_id, line)
        await self._bom_log(user, task_id, "ADD", {"name": line["name"], "qty": str(data.qty), "unit": line["unit"]})
        return await self.detail(user, task_id)

    async def edit_line(self, user: CurrentUser, bom_id: UUID, data: LineEditIn) -> dict[str, Any]:
        line = await self.repo.line(bom_id)
        if line is None:
            raise NotFoundError("Material")
        await self._bom_task(user, line.task_id)
        new = {"name": data.name.strip(), "qty": data.qty, "unit": data.unit.strip()}
        await self.repo.update_line(bom_id, new)
        await self._bom_log(user, line.task_id, "EDIT", {
            "before": {"name": line.name, "qty": str(line.qty), "unit": line.unit},
            "after": {"name": new["name"], "qty": str(data.qty), "unit": new["unit"]}})
        return await self.detail(user, line.task_id)

    async def delete_line(self, user: CurrentUser, bom_id: UUID) -> dict[str, Any]:
        line = await self.repo.line(bom_id)
        if line is None:
            raise NotFoundError("Material")
        await self._bom_task(user, line.task_id)
        await self.repo.delete_line(bom_id)
        await self._bom_log(user, line.task_id, "DELETE",
                            {"name": line.name, "qty": str(line.qty), "unit": line.unit})
        return await self.detail(user, line.task_id)

    async def add_to_catalog(self, user: CurrentUser, task_id: UUID, data: CatalogAddIn) -> dict[str, Any]:
        """PM menyimpan material di luar katalog ke katalog jenis titik (dipakai survei berikutnya)."""
        task, _ = await self._task(user, task_id, DailyNeed.MANAGE)
        if str(data.point_type_id) not in {str(t["work_type_id"]) for t in await self._point_types(task)}:
            raise ValidationError("Jenis titik tidak tersedia untuk survei divisi ini.")
        if not await self.repo.add_catalog(data.point_type_id, data.name.strip(), data.unit.strip()):
            raise AppError("DUPLICATE", "Material itu sudah ada di katalog jenis titik ini.", status=409)
        return await self.detail(user, task_id)

    # ── PM ────────────────────────────────────────────────────────────────────
    async def review(self, user: CurrentUser, task_id: UUID, data: ReviewIn) -> dict[str, Any]:
        task, _ = await self._task(user, task_id, DailyNeed.MANAGE)
        if survey_state(task) != "SUBMITTED":
            raise _state("Hanya survei yang sudah dikirim dan belum diputuskan yang bisa ditinjau.")
        approve = data.decision == "APPROVE"
        await self.repo.set_task_state(task.item_id, done=approve, approver=user.employee_id if approve else None)
        await self.repo.log(user.user_id, user.role or "", task_id,
                            "SURVEY_APPROVED" if approve else "SURVEY_RETURNED", {"note": (data.note or "").strip()})
        return await self.detail(user, task_id)

    async def plan_from_survey(
        self, user: CurrentUser, task_id: UUID, data: PlanFromSurveyIn
    ) -> tuple[UUID, list[UUID]]:
        task, _ = await self._task(user, task_id, DailyNeed.MANAGE)
        if survey_state(task) != "APPROVED":
            raise _state("Setujui survei terlebih dahulu.")
        if data.daily_plan_id:
            target = await self.repo.plan_target(data.daily_plan_id)
        elif data.work_date:
            chosen_team_id = data.team_id or task.team_id
            target = await self.repo.team_day(chosen_team_id, data.work_date)
            if target is None and data.work_date >= task.work_date:
                await self.repo.draft_day(task.daily_plan_id, data.work_date, user.employee_id, team_id=chosen_team_id)
                target = await self.repo.team_day(chosen_team_id, data.work_date)
        else:
            raise ValidationError("Pilih tanggal atau jadwal tujuan.")
        if target is None:
            raise NotFoundError("Jadwal harian")
        await check_daily_access(self.db, target.daily_plan_id, user, DailyNeed.MANAGE)
        if target.status not in PLANNABLE:
            raise _state(f"Jadwal tim pada {target.work_date:%d-%m-%Y} sudah diterbitkan. "
                         "Pilih tanggal lain, atau tambahkan lewat perubahan jadwal.")
        if str(target.division_id) != str(task.division_id):
            raise ValidationError("Jadwal lanjutan harus di divisi yang sama dengan survei.")
        if target.work_date < task.work_date:
            raise ValidationError("Jadwal lanjutan harus pada atau setelah tanggal survei.")
        for wt in filter(None, (data.work_type_id, data.preparation_work_type_id)):
            if await self.repo.work_type_division(wt) != str(task.division_id):
                raise ValidationError("Jenis pekerjaan lanjutan harus template divisi survei ini.")
        points = await self.repo.points(task_id)
        wanted = {str(p) for p in data.point_ids}
        chosen = [p for p in points if not wanted or str(p.point_id) in wanted]
        if not chosen:
            raise ValidationError("Pilih minimal satu titik survei.")
        # Jenis pemasangan per titik: pilihan PM, atau pemasangan lanjutan bawaan jenis titiknya.
        follow_ups = {str(t["work_type_id"]): t["follow_up_work_type_id"] for t in await self._point_types(task)}
        install: dict[str, Any] = {}
        missing: list[str] = []
        for p in chosen:
            install_wt = data.work_type_id or follow_ups.get(str(p.work_type_id))
            if install_wt is None:
                missing.append(p.name)
            install[str(p.point_id)] = install_wt
        if missing:
            raise ValidationError("Pilih jenis pekerjaan pemasangan — jenis titik ini belum punya pemasangan "
                                  f"bawaan: {', '.join(missing)}.")
        lines = await self.repo.lines([str(p.point_id) for p in chosen])
        needs: dict[str, list[str]] = {}
        materials: dict[str, list[str]] = {}
        for ln in lines:
            label = f"{ln.name} {Decimal(ln.qty).normalize():f} {ln.unit}".strip()
            if ln.category == "KEBUTUHAN":
                needs.setdefault(str(ln.point_id), []).append(ln.name)
            elif ln.category == "MATERIAL":
                materials.setdefault(str(ln.point_id), []).append(label)
        # Urutan per titik tetap: persiapan (bila ada kebutuhan), lalu pemasangan. Ditulis dalam satu INSERT.
        new_rows: list[tuple[Any, str, Any, str | None]] = []
        for p in chosen:
            pid = str(p.point_id)
            if data.preparation_work_type_id and needs.get(pid):
                new_rows.append((data.preparation_work_type_id, "PREPARATION", p,
                                 "Kebutuhan: " + ", ".join(needs[pid])))
            note = "\n".join(filter(None, [
                ("Material: " + "; ".join(materials[pid])) if materials.get(pid) else None,
                ("Kebutuhan: " + ", ".join(needs[pid])) if needs.get(pid) else None,
                p.notes,
            ]))
            new_rows.append((install[pid], data.task_phase, p, note[:4000] or None))
        created: list[UUID] = await self.repo.insert_follow_ups(target.daily_plan_id, task.completion_id, new_rows)
        await self.repo.log(user.user_id, user.role or "", task_id, "SURVEY_PLANNED",
                            {"daily_plan_id": str(target.daily_plan_id), "items": len(created)})
        return target.daily_plan_id, created
