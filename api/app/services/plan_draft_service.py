"""
app/services/plan_draft_service.py
Form "Buat SK" / "Ubah isi SK" alur v2 (keputusan pemilik 2026-10-03, flowchart SK2-A/B).

Satu simpan = satu transaksi: SK, lokasi baru, hari & detail pekerjaan, tim, alat, kendaraan, driver.
Aturan pilihan (dikonfirmasi pemilik):
- ketua: staf lapangan (bukan akun kantor) yang tidak terikat SK aktif mana pun;
- anggota: syarat sama + bawahan PM (unit yang sama) + bukan ketua terpilih;
- alat/kendaraan: siap pakai, tidak teralokasi, tidak dipinjam;
- driver: ketua/anggota terpilih dengan SIM sesuai tipe kendaraan (roda dua = SIM C) yang tidak terikat SK lain.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PlanStatus
from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError, trigger_rule_error
from app.core.permissions import RoleCode
from app.core.security import CurrentUser
from app.crud.crud_asset_reservation import CRUDAssetReservation
from app.crud.crud_plan_draft import CRUDPlanDraft
from app.schemas.plan_draft import PlanDraftRequest
from app.services.access_service import ensure_same_org
from app.services.work_type_service import WorkTypeService

CATEGORIES = {"INSTALASI": "Instalasi", "PEMELIHARAAN": "Pemeliharaan", "PERBAIKAN": "Perbaikan",
              "SURVEI": "Survei", "LAINNYA": "Lainnya"}
MAX_TASKS_PER_DAY = 30


def _day_roster(data: PlanDraftRequest, day: Any) -> list[UUID] | None:
    """Daftar orang yang bertugas pada satu hari: None = seluruh tim; bila ada daftar khusus, ketua selalu ikut."""
    if day.member_employee_ids is None:
        return None
    return [data.leader_employee_id, *[m for m in day.member_employee_ids if m != data.leader_employee_id]]


def _invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, status=422)


def licence_for(vehicle_type: str | None) -> str:
    """Sama dengan trigger tg_vehicle_driver_licence: roda dua → SIM C, selain itu SIM A."""
    return "SIM C" if vehicle_type == "MOTORCYCLE" else "SIM A"


class PlanDraftService:
    """
    Layanan untuk mengelola proses penyusunan draf Surat Keputusan (SK).
    Menangani pengambilan data form, validasi aturan bisnis, serta penyimpanan SK dan komponennya.
    """
    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi PlanDraftService.

        Args:
            db (AsyncSession): Sesi database asinkron.
        """
        self.db = db
        self.repo = CRUDPlanDraft(db)
        self.assets = CRUDAssetReservation(db)

    async def _creator(self, user: CurrentUser) -> Any:
        """
        Mengambil profil karyawan pembuat SK berdasarkan pengguna yang login.

        Args:
            user (CurrentUser): Pengguna yang sedang login.

        Returns:
            Any: Data kreator/pembuat SK.
        """
        creator = await self.repo.creator(user.user_id)
        if creator is None or not creator.unit_id:
            raise ForbiddenError("Akun Anda belum tertaut ke data karyawan aktif pada sebuah unit.")
        return creator

    @staticmethod
    def _oversees(user: CurrentUser) -> bool:
        """
        Memeriksa apakah pengguna memiliki peran pengawas (ADMIN atau OPS).

        Args:
            user (CurrentUser): Pengguna.

        Returns:
            bool: True jika ADMIN/OPS, sebaliknya False.
        """
        return RoleCode.ADMIN in user.roles or RoleCode.OPS in user.roles

    # ── Pilihan form ──────────────────────────────────────────────────────────────────────────
    async def form_options(self, user: CurrentUser, plan_id: UUID | None) -> dict[str, Any]:
        """
        Mendapatkan seluruh opsi yang diperlukan untuk mengisi form draf SK (unit, lokasi, personel, alat, dsb).

        Args:
            user (CurrentUser): Pengguna.
            plan_id (UUID | None): ID SK (jika sedang mengedit, untuk mengecualikan aset/orang yang sudah terikat SK ini).

        Returns:
            dict[str, Any]: Kamus berisi opsi kategori, lokasi, calon ketua, calon anggota, dsb.
        """
        creator = await self._creator(user)
        unit = creator.unit_id
        assets = await self.repo.free_assets(user.organization_id, plan_id)
        return {
            "unit_name": creator.unit_name,
            "categories": [{"code": k, "label": v} for k, v in CATEGORIES.items()],
            "sites": await self.repo.sites(user.organization_id, None if self._oversees(user) else unit),
            "leaders": await self.repo.field_staff(user.organization_id, unit, plan_id),
            "members": await self.repo.field_staff(user.organization_id, unit, plan_id),
            "tools": [a for a in assets if a.kind == "TOOL"],
            "vehicles": [a for a in assets if a.kind == "VEHICLE"],
        }

    async def driver_options(self, user: CurrentUser, vehicle_id: UUID, candidate_ids: list[UUID],
                             period_end: date, plan_id: UUID | None) -> list[str]:
        """
        Calon driver (dari ketua + anggota terpilih) yang ber-SIM sesuai dan tidak terikat SK lain.

        Args:
            user (CurrentUser): Pengguna pembuat request.
            vehicle_id (UUID): ID kendaraan yang diplih.
            candidate_ids (list[UUID]): Daftar ID personel.
            period_end (date): Tanggal akhir SK.
            plan_id (UUID | None): ID SK yang sedang diedit.

        Returns:
            list[str]: Daftar ID karyawan yang dapat mengemudikan kendaraan tersebut.
        """
        vehicle = next((a for a in await self.repo.free_assets(user.organization_id, plan_id)
                        if str(a.id) == str(vehicle_id) and a.kind == "VEHICLE"), None)
        if vehicle is None:
            raise NotFoundError("Kendaraan")
        ids = [str(c) for c in candidate_ids]
        licensed = await self.repo.licensed(ids, licence_for(vehicle.vehicle_type), period_end)
        bound = await self.repo.employees_bound(ids, plan_id)
        return [i for i in ids if i in licensed and i not in bound]

    # ── Validasi isi form ─────────────────────────────────────────────────────────────────────
    async def _validate(self, user: CurrentUser, unit_id: str, data: PlanDraftRequest,
                        plan_id: UUID | None) -> None:
        """
        Melakukan validasi seluruh komponen isi PlanDraftRequest, mencakup kelengkapan data,
        konsistensi tanggal harian, status dan unit personel (R-17), serta status aset.

        Args:
            user (CurrentUser): Pengguna.
            unit_id (str): ID Unit pembuat SK.
            data (PlanDraftRequest): Data payload form.
            plan_id (UUID | None): ID SK jika ini update.
        """
        if not data.title.strip():
            raise _invalid("Judul pekerjaan wajib diisi.")
        if not data.description.strip():
            raise _invalid("Deskripsi pekerjaan wajib diisi.")
        if data.period_end < data.period_start:
            raise _invalid("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        if data.site_id is None and data.new_site is None:
            raise _invalid("Pilih lokasi kerja atau tambahkan lokasi baru.")
        await WorkTypeService(self.db).ensure_plan_type(user.organization_id, plan_id, data.work_type_id)
        if data.new_site is not None and not data.new_site.name.strip():
            raise _invalid("Nama lokasi wajib diisi.")

        expected = {data.period_start + timedelta(days=i)
                    for i in range((data.period_end - data.period_start).days + 1)}
        given = [d.work_date for d in data.days]
        # Tanggal yang tidak ada di daftar = hari libur (dikeluarkan dari rencana, 2026-10-09).
        if not given or len(given) != len(set(given)) or not set(given) <= expected:
            raise _invalid("Hari kerja harus berada dalam rentang rencana kerja dan tidak boleh kembar.")
        if min(given) != data.period_start or max(given) != data.period_end:
            raise _invalid("Tanggal mulai dan selesai harus hari kerja (bukan hari libur).")
        files: list[UUID] = []
        for day in data.days:
            if not 1 <= len(day.tasks) <= MAX_TASKS_PER_DAY:
                raise _invalid(f"Isi 1 sampai {MAX_TASKS_PER_DAY} detail pekerjaan per hari ({day.work_date:%d-%m-%Y}).")
            for task in day.tasks:
                if not task.title.strip() or not task.description.strip():
                    raise _invalid(f"Judul dan deskripsi setiap detail pekerjaan wajib diisi ({day.work_date:%d-%m-%Y}).")
                files.extend(task.file_ids)
        if files and len(await self.repo.org_files(files, user.organization_id)) != len(set(map(str, files))):
            raise NotFoundError("Berkas")

        leader = str(data.leader_employee_id)
        members = [str(m) for m in data.member_employee_ids]
        team = {leader, *members}
        for day in data.days:
            if day.member_employee_ids is not None and not {str(m) for m in day.member_employee_ids} <= team:
                raise _invalid(f"Anggota hari {day.work_date:%d-%m-%Y} harus termasuk tim rencana kerja.")
        day_sites = {d.site_id for d in data.days if d.site_id is not None}
        if day_sites:
            await ensure_same_org(self.db, user.organization_id, sites=day_sites)
        if leader in members or len(set(members)) != len(members):
            raise _invalid("Ketua tim tidak boleh dipilih lagi sebagai anggota.")
        staff = await self.repo.field_staff_ids([leader, *members], user.organization_id)
        if {leader, *members} - set(staff):
            raise AppError("PERSONNEL_NOT_FIELD_STAFF",
                           "Ketua dan anggota tim hanya dapat dipilih dari staf lapangan (bukan akun kantor).",
                           status=422)
        # Keputusan pemilik 2026-10-06: ketua juga harus bawahan PM (unit yang sama), seperti anggota.
        if any(staff[m] != unit_id for m in (leader, *members)):
            raise AppError("PERSONNEL_OUTSIDE_PM_UNIT", "Ketua dan anggota tim harus bawahan PM (unit yang sama).", status=422)
        if await self.repo.employees_bound([leader, *members], plan_id):
            raise AppError("PERSONNEL_BOUND", "Ada ketua/anggota yang masih terikat rencana kerja lain.", status=409)

        free = {str(a.id): a for a in await self.repo.free_assets(user.organization_id, plan_id)}
        for tool in data.tool_ids:
            if str(tool) not in free or free[str(tool)].kind != "TOOL":
                raise AppError("ASSET_UNAVAILABLE", "Ada alat yang tidak lagi tersedia. Muat ulang pilihan.", status=409)
        if data.vehicle_id is not None:
            vehicle = free.get(str(data.vehicle_id))
            if vehicle is None or vehicle.kind != "VEHICLE":
                raise AppError("ASSET_UNAVAILABLE", "Kendaraan tidak lagi tersedia. Muat ulang pilihan.", status=409)
            if data.driver_employee_id is None:
                raise _invalid("Pilih driver kendaraan.")
            driver = str(data.driver_employee_id)
            if driver not in {leader, *members}:
                raise _invalid("Driver harus ketua atau anggota tim yang dipilih.")
            needed = licence_for(vehicle.vehicle_type)
            if driver not in await self.repo.licensed([driver], needed, data.period_end):
                raise _invalid(f"Driver tidak memiliki {needed} yang berlaku sampai tanggal selesai.")

    async def _site(self, user: CurrentUser, unit_id: str, data: PlanDraftRequest) -> tuple[str, str]:
        """
        Menyimpan data lokasi baru atau mencari nama lokasi lama.

        Args:
            user (CurrentUser): Pengguna.
            unit_id (str): ID Unit pembuat.
            data (PlanDraftRequest): Data payload form.

        Returns:
            tuple[str, str]: Pasangan ID lokasi dan Nama lokasi.
        """
        if data.new_site is not None:
            try:
                async with self.db.begin_nested():
                    site = await self.repo.insert_site(user.organization_id, unit_id, data.new_site.name.strip(),
                                                       (data.new_site.description or "").strip() or None,
                                                       data.new_site.lat, data.new_site.lng)
            except IntegrityError:
                raise AppError("SITE_INVALID", "Nama lokasi sudah dipakai. Pilih dari daftar atau ganti nama.",
                               status=409) from None
            return str(site.id), str(site.name)
        name = await self.repo.site_name(data.site_id or "", user.organization_id)
        if name is None:
            raise NotFoundError("Lokasi")
        return str(data.site_id), name

    async def _fill(self, user: CurrentUser, plan_id: str, data: PlanDraftRequest) -> None:
        """
        Mengisi relasi plan: hari, task, file, anggota tim, serta reservasi alat & kendaraan.

        Args:
            user (CurrentUser): Pengguna pembuat request.
            plan_id (str): ID SK terkait.
            data (PlanDraftRequest): Data payload form yang berisi daftar list.
        """
        for order, day in enumerate(sorted(data.days, key=lambda d: d.work_date)):
            day_id = await self.repo.insert_day(plan_id, day.work_date, day.tasks[0].title.strip(), order, day.site_id)
            await self.repo.set_day_members(user.organization_id, day_id, _day_roster(data, day))
            for t_order, task in enumerate(day.tasks):
                task_id = await self.repo.insert_task(day_id, task.title.strip(), task.description.strip(), t_order)
                for f_order, file_id in enumerate(dict.fromkeys(task.file_ids)):
                    await self.repo.insert_task_file(task_id, file_id, f_order)
        try:
            await self.repo.insert_member(plan_id, data.leader_employee_id, "LEADER", data.period_start)
            for member in data.member_employee_ids:
                await self.repo.insert_member(plan_id, member, "MEMBER", data.period_start)
            for tool in data.tool_ids:
                await self.assets.insert_allocation(tool, plan_id, None, user.user_id)
                await self.assets.set_asset_status(tool, "RESERVED")
            if data.vehicle_id is not None:
                await self.assets.insert_allocation(data.vehicle_id, plan_id, data.driver_employee_id, user.user_id)
                await self.assets.set_asset_status(data.vehicle_id, "RESERVED")
        except IntegrityError as exc:
            rule = trigger_rule_error(exc)
            raise (rule or AppError("CONFLICT", "Jadwal bentrok dengan rencana kerja lain. Muat ulang pilihan.",
                                    status=409)) from None

    # ── Simpan ────────────────────────────────────────────────────────────────────────────────
    async def create_plan(self, user: CurrentUser, data: PlanDraftRequest) -> Any:
        """
        domain.js CREATE_PLAN versi form lengkap — hasilnya status Draf.

        Args:
            user (CurrentUser): Pengguna yang membuat SK.
            data (PlanDraftRequest): Payload form data SK.

        Returns:
            Any: Detail dari SK yang baru dibuat.
        """
        creator = await self._creator(user)
        # Memvalidasi seluruh data input secara berurutan
        await self._validate(user, creator.unit_id, data, None)
        # Menyimpan atau mengambil ID lokasi baru/lama
        site_id, site_name = await self._site(user, creator.unit_id, data)
        # Menyisipkan record utama SK ke dalam database
        row = await self.repo.insert_plan(
            user.organization_id, creator.unit_id, user.user_id, title=data.title.strip(),
            description=data.description.strip(), category=data.category, site_id=site_id,
            location_text=site_name, period_start=data.period_start, period_end=data.period_end,
            pm_employee_id=creator.employee_id, leader_employee_id=data.leader_employee_id,
            is_out_of_town=data.is_out_of_town, work_type_id=data.work_type_id)
        # Menyisipkan relasi (tugas harian, tim, reservasi aset)
        await self._fill(user, str(row.id), data)
        return await self.detail(row.id)

    async def edit_draft(self, user: CurrentUser, plan_id: UUID, data: PlanDraftRequest) -> Any:
        """
        domain.js EDIT_DRAFT versi form lengkap — isi draf disusun ulang seluruhnya.

        Args:
            user (CurrentUser): Pengguna pengubah.
            plan_id (UUID): ID SK.
            data (PlanDraftRequest): Data terbaru untuk menimpa draf lama.

        Returns:
            Any: Detail dari SK yang sudah diperbarui.
        """
        plan = await self.repo.lock_draft(plan_id, user.organization_id)
        if plan is None:
            raise NotFoundError("Rencana Kerja")
        # Validasi status harus DRAFT
        if plan.status != PlanStatus.DRAFT:
            raise AppError("INVALID_STATE", "Isi rencana kerja hanya dapat diubah selama berstatus Draf.", status=409)
        if data.row_version is None or plan.row_version != data.row_version:
            raise ConflictError()
        unit_id = str(plan.unit_id)
        # Validasi kembali seluruh input baru
        await self._validate(user, unit_id, data, plan_id)
        # Menghapus seluruh relasi lama (tim, aset, pekerjaan harian)
        await self.repo.clear_draft_parts(plan_id)
        site_id, site_name = await self._site(user, unit_id, data)
        # Memperbarui record utama SK
        await self.repo.update_plan(
            plan_id, title=data.title.strip(), description=data.description.strip(), category=data.category,
            site_id=site_id, location_text=site_name, period_start=data.period_start, period_end=data.period_end,
            leader_employee_id=data.leader_employee_id, is_out_of_town=data.is_out_of_town,
            work_type_id=data.work_type_id)
        # Memasukkan kembali relasi (tugas harian, tim, reservasi aset) dengan data baru
        await self._fill(user, str(plan_id), data)
        return await self.detail(plan_id)

    async def detail(self, plan_id: UUID | str, include_drafts: bool = False) -> dict[str, Any]:
        """
        Mengambil representasi lengkap (detail dan seluruh relasinya) untuk satu SK.

        Args:
            plan_id (UUID | str): ID SK.
            include_drafts (bool): Hanya ketua yang boleh melihat laporan harian berstatus Draf; PM/anggota tidak.

        Returns:
            dict[str, Any]: Kamus detail SK beserta relasinya.
        """
        value = await self.repo.plan_detail(plan_id)
        detail: dict[str, Any] = json.loads(value) if isinstance(value, str) else value
        if not include_drafts:   # Draf belum dikirim: tidak boleh terlihat PM seolah-olah sudah terkirim
            for day in detail.get("days", []):
                if (day.get("report") or {}).get("status") == "DRAFT":
                    day["report"] = None
        category = detail["plan"].get("category")
        detail["plan"]["category_label"] = CATEGORIES.get(category, category) if category else None
        return detail
