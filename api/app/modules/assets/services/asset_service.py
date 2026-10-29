"""
app/modules/assets/services/asset_service.py
Inventaris aset (Milestone 4, docs/36; alur docs/35 §6): alat pribadi/umum, kendaraan, serah terima & pengembalian.

- Lihat inventaris: semua pengguna yang login. Kelola master, berkas kendaraan & serah terima: `manage:assets`
  (HR/GA, SUPER_ADMIN).
- Status `allocated`/`loaned` hanya lewat serah terima: dikaitkan ke jadwal harian → `allocated`, pinjaman
  pribadi → `loaned`. Status manual hanya ready/damaged/lost/pension dan tidak bisa saat aset sedang dipinjam.
- Serah terima: aset harus `ready`; karyawan aktif (bukan sedang offboarding); alat PERSONAL_LOAN tidak
  dikaitkan ke jadwal; jadwal harus belum lewat dan karyawan anggota tim jadwal itu.
- Kendaraan: STNK berlaku wajib, KIR berlaku wajib untuk Truck, dan pemegang punya SIM yang berlaku sesuai jenis
  (Motorcycle → SIM C; Car/Truck → SIM A atau SIM B I/II).
- Pengembalian menutup peminjaman (`returned_at`) dengan kondisi ready/damaged/lost yang juga menjadi status aset.
- Inspeksi kendaraan: pengelola aset atau pemegang kendaraan saat itu.
- Pengajuan pinjam: karyawan mengajukan untuk dirinya sendiri; pengelola aset (HR/GA) menyetujui -> serah
  terima biasa (`lend`) atau menolak. Pengajuan pengembalian: pemegang aset mengirim kondisi + foto;
  pengelola mengonfirmasi lewat pengembalian biasa.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.assets.repositories.asset_repository import AssetRepository
from app.modules.assets.schemas.asset_schema import (
    InspectionCreate,
    LoanCreate,
    LoanRequestCreate,
    LoanRequestReview,
    LoanReturnRequest,
    ToolCreate,
    ToolUpdate,
    VehicleCreate,
    VehicleFileCreate,
    VehicleUpdate,
)
from app.modules.notifications.services.notification_service import NotificationService
from app.shared.access.access_service import DailyNeed, check_daily_access

LICENCES = {
    "Motorcycle": ({"SIM_C"}, "SIM C"),
    "Car": ({"SIM_A", "SIM_B1", "SIM_B2"}, "SIM A atau SIM B"),
    "Truck": ({"SIM_A", "SIM_B1", "SIM_B2"}, "SIM A atau SIM B"),
}
_LABEL = {"TOOL": "Alat", "VEHICLE": "Kendaraan"}


def _in_use(asset_type: str) -> AppError:
    return AppError(
        "ASSET_IN_USE", f"{_LABEL[asset_type]} sedang dipinjam. Selesaikan pengembaliannya dulu.", status=409
    )


_NIL_UUID = "00000000-0000-0000-0000-000000000000"


class AssetService:
    """Use case inventaris & peminjaman aset."""

    def __init__(self, repo: AssetRepository) -> None:
        self.repo = repo

    def _notify(self) -> NotificationService:
        return NotificationService(self.repo.db)

    # ── Rujukan ────────────────────────────────────────────────────────────────
    async def _path(self, file_id: UUID | None, what: str) -> str | None:
        if file_id is None:
            return None
        key = await self.repo.file_key(file_id)
        if key is None:
            raise ValidationError(f"Berkas {what} belum diunggah atau sudah dihapus. Unggah ulang berkasnya.")
        return key

    async def _check_place(self, office_id: UUID | None, division_id: UUID | None) -> None:
        if office_id and not await self.repo.office_exists(office_id):
            raise ValidationError("Kantor tidak ditemukan atau sudah dihapus.")
        if division_id and not await self.repo.division_active(division_id):
            raise ValidationError("Divisi tidak ditemukan atau sudah nonaktif.")

    # ── Alat ───────────────────────────────────────────────────────────────────
    async def list_tools(self, office_id: UUID | None, status: str | None) -> list[Any]:
        return await self.repo.list_tools(office_id, status)

    async def _tool(self, tool_id: UUID) -> Any:
        tool = await self.repo.get_tool(tool_id)
        if tool is None:
            raise NotFoundError("Alat")
        return tool

    async def create_tool(self, data: ToolCreate) -> Any:
        await self._check_place(data.office_id, data.division_id)
        if await self.repo.tool_code_taken(data.tool_code):
            raise AppError("TOOL_CODE_TAKEN", "Kode alat sudah dipakai.", status=409)
        fields = data.model_dump(exclude={"photo_file_id"})
        fields.update(office_id=str(data.office_id), division_id=str(data.division_id) if data.division_id else None,
                      name=data.name.strip(), photo_path=await self._path(data.photo_file_id, "foto"))
        return await self.repo.get_tool(await self.repo.insert_tool(fields))

    async def update_tool(self, tool_id: UUID, data: ToolUpdate) -> Any:
        tool = await self._tool(tool_id)
        await self._check_place(data.office_id, data.division_id)
        if data.tool_code and await self.repo.tool_code_taken(data.tool_code, exclude=tool_id):
            raise AppError("TOOL_CODE_TAKEN", "Kode alat sudah dipakai.", status=409)
        if data.ownership_type and data.ownership_type != tool.ownership_type and tool.assignment_id:
            raise _in_use("TOOL")
        fields = data.model_dump(exclude={"photo_file_id"})
        fields.update(office_id=str(data.office_id) if data.office_id else None,
                      division_id=str(data.division_id) if data.division_id else None,
                      name=data.name.strip() if data.name else None,
                      photo_path=await self._path(data.photo_file_id, "foto"))
        await self.repo.update_tool(tool_id, fields)
        return await self.repo.get_tool(tool_id)

    # ── Kendaraan ──────────────────────────────────────────────────────────────
    async def list_vehicles(self, office_id: UUID | None, status: str | None) -> list[Any]:
        return await self.repo.list_vehicles(office_id, status)

    async def _vehicle(self, vehicle_id: UUID) -> Any:
        vehicle = await self.repo.get_vehicle(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Kendaraan")
        return vehicle

    async def create_vehicle(self, data: VehicleCreate) -> Any:
        await self._check_place(data.office_id, data.division_id)
        if await self.repo.plate_taken(data.number_plate):
            raise AppError("PLATE_TAKEN", "Nomor polisi sudah terdaftar.", status=409)
        fields = data.model_dump(exclude={"photo_file_id"})
        fields.update(office_id=str(data.office_id), division_id=str(data.division_id), name=data.name.strip(),
                      photo_path=await self._path(data.photo_file_id, "foto"))
        return await self.repo.get_vehicle(await self.repo.insert_vehicle(fields))

    async def update_vehicle(self, vehicle_id: UUID, data: VehicleUpdate) -> Any:
        vehicle = await self._vehicle(vehicle_id)
        await self._check_place(data.office_id, data.division_id)
        if data.number_plate and await self.repo.plate_taken(data.number_plate, exclude=vehicle_id):
            raise AppError("PLATE_TAKEN", "Nomor polisi sudah terdaftar.", status=409)
        if data.vehicle_type and data.vehicle_type != vehicle.vehicle_type and vehicle.assignment_id:
            raise _in_use("VEHICLE")
        fields = data.model_dump(exclude={"photo_file_id"})
        fields.update(office_id=str(data.office_id) if data.office_id else None,
                      division_id=str(data.division_id) if data.division_id else None,
                      name=data.name.strip() if data.name else None,
                      photo_path=await self._path(data.photo_file_id, "foto"))
        await self.repo.update_vehicle(vehicle_id, fields)
        return await self.repo.get_vehicle(vehicle_id)

    # ── Status & arsip ────────────────────────────────────────────────────────
    async def set_status(self, asset_type: str, asset_id: UUID, status: str) -> Any:
        if await self.repo.lock_asset(asset_type, asset_id) is None:
            raise NotFoundError(_LABEL[asset_type])
        if await self.repo.has_open_loan(asset_type, asset_id):
            raise _in_use(asset_type)
        await self.repo.set_status(asset_type, asset_id, status)
        return await (self.repo.get_tool(asset_id) if asset_type == "TOOL" else self.repo.get_vehicle(asset_id))

    async def delete(self, asset_type: str, asset_id: UUID) -> None:
        if await self.repo.lock_asset(asset_type, asset_id) is None:
            raise NotFoundError(_LABEL[asset_type])
        if await self.repo.has_open_loan(asset_type, asset_id):
            raise _in_use(asset_type)
        await self.repo.archive(asset_type, asset_id)

    # ── Berkas & inspeksi kendaraan ───────────────────────────────────────────
    async def vehicle_files(self, vehicle_id: UUID) -> list[Any]:
        await self._vehicle(vehicle_id)
        return await self.repo.vehicle_files(vehicle_id)

    async def add_vehicle_file(self, vehicle_id: UUID, data: VehicleFileCreate) -> list[Any]:
        await self._vehicle(vehicle_id)
        path = await self._path(data.file_id, data.type)
        assert path is not None
        await self.repo.insert_vehicle_file(vehicle_id, data.type, path, data.active_at, data.expired_at)
        return await self.repo.vehicle_files(vehicle_id)

    async def inspections(self, vehicle_id: UUID) -> list[Any]:
        await self._vehicle(vehicle_id)
        return await self.repo.inspections(vehicle_id)

    async def add_inspection(self, user: CurrentUser, vehicle_id: UUID, data: InspectionCreate) -> list[Any]:
        vehicle = await self._vehicle(vehicle_id)
        inspector = await self.repo.employee_of_user(user.user_id)
        manager = Permission.MANAGE_ASSETS.value in user.permissions
        if not manager and (inspector is None or str(vehicle.holder_employee_id) != inspector):
            raise ForbiddenError("Inspeksi hanya oleh pengelola aset atau pemegang kendaraan saat ini.")
        path = await self._path(data.file_id, "inspeksi")
        assert path is not None
        await self.repo.insert_inspection(vehicle_id, inspector, data.type, path)
        return await self.repo.inspections(vehicle_id)

    # ── Peminjaman ────────────────────────────────────────────────────────────
    async def availability(self, work_date: date, team_id: UUID | None) -> list[dict[str, Any]]:
        """Ketersediaan alat & kendaraan pada tanggal jadwal: tersedia, atau dipakai tim mana."""
        rows = await self.repo.availability(work_date)
        names = await self.repo.team_names([r.team_id for r in rows])
        out: list[dict[str, Any]] = []
        for r in rows:
            used_by = str(r.team_id) if r.team_id else None
            out.append({
                "asset_type": r.asset_type,
                "asset_id": r.asset_id,
                "asset_name": r.asset_name,
                "status": r.status,
                "available": used_by is None and r.status in ("ready", "allocated", "loaned"),
                "used_by_team_id": used_by,
                "used_by_team_name": names.get(used_by) if used_by else None,
                "used_by_requested_team": bool(used_by and team_id and used_by == str(team_id)),
            })
        return out

    async def loans(
        self, user: CurrentUser, *, open_only: bool, employee_id: UUID | None, daily_plan_id: UUID | None
    ) -> list[Any]:
        """Pengelola aset (MANAGE_ASSETS) melihat semua. Pemegang VIEW_TEAMS hanya melihat pinjaman jadwal yang
        ia kelola (atau tim jadwalnya sendiri) dan pinjaman karyawan di divisi yang ia pimpin; selain itu hanya
        pinjaman miliknya sendiri."""
        perms = set(user.permissions)
        own = await self.repo.employee_of_user(user.user_id)
        if Permission.MANAGE_ASSETS.value in perms:
            if daily_plan_id and await self.repo.plan_for_loan(daily_plan_id, own or _NIL_UUID) is None:
                raise NotFoundError("Jadwal harian")
            return await self.repo.loans(open_only=open_only, employee_id=employee_id,
                                         daily_plan_id=daily_plan_id, managed_by=None)
        if own is None:
            return []
        if daily_plan_id:
            await check_daily_access(self.repo.db, daily_plan_id, user, DailyNeed.VIEW)
            plan = await self.repo.plan_for_loan(daily_plan_id, own)
            if plan is not None and (plan.on_team or (Permission.VIEW_TEAMS.value in perms and plan.manages)):
                return await self.repo.loans(open_only=open_only, employee_id=employee_id,
                                             daily_plan_id=daily_plan_id, managed_by=None)
            return await self.repo.loans(open_only=open_only, employee_id=UUID(own),
                                         daily_plan_id=daily_plan_id, managed_by=None)
        if Permission.VIEW_TEAMS.value in perms:
            return await self.repo.loans(open_only=open_only, employee_id=employee_id,
                                         daily_plan_id=None, managed_by=own)
        return await self.repo.loans(open_only=open_only, employee_id=UUID(own), daily_plan_id=None, managed_by=None)

    async def _check_vehicle_papers(self, vehicle_id: UUID, vehicle_type: str, employee_id: UUID) -> None:
        vehicle = await self._vehicle(vehicle_id)
        today = jakarta_now().date()
        if vehicle.stnk_expired_at is None or vehicle.stnk_expired_at < today:
            raise AppError("VEHICLE_PAPERS_EXPIRED", "STNK kendaraan tidak ada atau sudah kedaluwarsa.", status=422)
        if vehicle_type == "Truck" and (vehicle.kir_expired_at is None or vehicle.kir_expired_at < today):
            raise AppError("VEHICLE_PAPERS_EXPIRED", "KIR truk tidak ada atau sudah kedaluwarsa.", status=422)
        allowed, label = LICENCES[vehicle_type]
        if not allowed & await self.repo.valid_licences(employee_id):
            raise AppError("DRIVER_LICENCE_REQUIRED", f"Pemegang kendaraan wajib punya {label} yang berlaku.",
                           status=422)

    async def lend(self, data: LoanCreate) -> Any:
        asset_id = data.tool_id or data.vehicle_id
        assert asset_id is not None
        asset = await self.repo.lock_asset(data.asset_type, asset_id)
        if asset is None:
            raise NotFoundError(_LABEL[data.asset_type])
        if not await self.repo.employee_active(data.employee_id):
            raise ValidationError("Karyawan tidak ditemukan, nonaktif, atau sedang proses keluar.")

        plan = None
        if data.daily_plan_id is not None:
            if data.asset_type == "TOOL" and asset.ownership_type == "PERSONAL_LOAN":
                raise ValidationError("Alat pribadi dipinjamkan ke karyawan, tidak dikaitkan ke jadwal harian.")
            plan = await self.repo.plan_for_loan(data.daily_plan_id, data.employee_id)
            if plan is None:
                raise ValidationError("Jadwal harian tidak ditemukan.")
            if plan.is_past:
                raise ValidationError("Jadwal harian sudah lewat.")
            if not plan.on_team:
                raise ValidationError("Karyawan bukan anggota tim pada jadwal harian ini.")

        # Bentrok dicek per tanggal: aset yang dipakai tim lain pada tanggal jadwal ini ditolak, pada tanggal lain
        # boleh. Pinjaman tanpa jadwal tetap bentrok dengan peminjaman berjalan apa pun.
        work_date = plan.work_date if plan is not None else None
        if asset.status not in ("ready", "allocated", "loaned"):
            raise AppError("ASSET_NOT_AVAILABLE", f"{_LABEL[data.asset_type]} tidak siap dipinjam.", status=409)
        conflict = await self.repo.open_loan_conflict(data.asset_type, asset_id, work_date)
        if conflict is not None:
            if work_date is None:
                msg = f"{_LABEL[data.asset_type]} sedang dipinjam dan belum dikembalikan."
            else:
                msg = (f"{_LABEL[data.asset_type]} sudah dipakai tim {conflict.team_name or 'lain'} "
                       f"pada {work_date.isoformat()}.")
            raise AppError("ASSET_NOT_AVAILABLE", msg, status=409)

        if data.asset_type == "VEHICLE":
            await self._check_vehicle_papers(asset_id, asset.vehicle_type, data.employee_id)

        status = "allocated" if data.daily_plan_id else "loaned"
        assignment_id = await self.repo.insert_loan(
            data.asset_type, asset_id, data.employee_id, data.daily_plan_id, status,
            await self._path(data.handover_file_id, "foto serah terima"),
        )
        await self.repo.set_status(data.asset_type, asset_id, status)
        return await self.repo.get_loan(assignment_id)

    async def return_loan(self, assignment_id: UUID, condition: str) -> Any:
        loan = await self.repo.open_loan_for_update(assignment_id)
        if loan is None:
            if await self.repo.get_loan(assignment_id) is None:
                raise NotFoundError("Peminjaman aset")
            raise AppError("ALREADY_RETURNED", "Aset ini sudah dikembalikan.", status=409)
        await self.repo.close_loan(assignment_id, condition)
        await self.repo.set_status(loan.asset_type, loan.asset_id, condition)
        done = await self.repo.get_loan(assignment_id)
        await self._notify().notify_employees(
            [done.employee_id], "ASSET_RETURNED", f"Pengembalian {done.asset_name} diterima", "", target="asset"
        )
        return done

    # ── Pengajuan pinjam & pengembalian oleh karyawan ──────────────────────────
    async def _own_employee(self, user: CurrentUser) -> UUID:
        own = await self.repo.employee_of_user(user.user_id)
        if own is None:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")
        return UUID(own)

    async def request_loan(self, user: CurrentUser, data: LoanRequestCreate) -> Any:
        employee_id = await self._own_employee(user)
        asset_id = data.tool_id or data.vehicle_id
        assert asset_id is not None
        asset = await self.repo.lock_asset(data.asset_type, asset_id)
        if asset is None:
            raise NotFoundError(_LABEL[data.asset_type])
        if asset.status != "ready" or await self.repo.has_open_loan(data.asset_type, asset_id):
            raise AppError("ASSET_NOT_AVAILABLE", f"{_LABEL[data.asset_type]} tidak siap dipinjam.", status=409)
        if await self.repo.has_pending_request(data.asset_type, asset_id, employee_id):
            raise AppError("REQUEST_EXISTS", "Pengajuan untuk aset ini masih menunggu persetujuan.", status=409)
        request_id = await self.repo.insert_request(
            data.asset_type, asset_id, employee_id, data.purpose.strip(), data.needed_on
        )
        req = await self.repo.get_request(request_id)
        await self._notify().notify_roles(
            ["ADMIN_HR_GA"], "ASSET_REQUESTED", f"{req.employee_name} mengajukan pinjam {req.asset_name}",
            data.purpose.strip(), target="asset",
        )
        return req

    async def requests(self, user: CurrentUser, *, status: str | None) -> list[Any]:
        if Permission.MANAGE_ASSETS.value in set(user.permissions):
            return await self.repo.requests(employee_id=None, status=status)
        own = await self.repo.employee_of_user(user.user_id)
        return [] if own is None else await self.repo.requests(employee_id=own, status=status)

    async def cancel_request(self, user: CurrentUser, request_id: UUID) -> Any:
        employee_id = await self._own_employee(user)
        req = await self.repo.request_for_update(request_id)
        if req is None:
            raise NotFoundError("Pengajuan pinjam aset")
        if str(req.employee_id) != str(employee_id):
            raise ForbiddenError("Hanya pemohon yang dapat membatalkan pengajuannya.")
        if req.status != "PENDING":
            raise AppError("NOT_CANCELLABLE", "Pengajuan ini sudah diputuskan.", status=409)
        await self.repo.set_request_status(request_id, "CANCELLED", None, None)
        req = await self.repo.get_request(request_id)
        await self._notify().notify_roles(
            ["ADMIN_HR_GA"], "ASSET_REQUEST_CANCELLED",
            f"{req.employee_name} membatalkan pengajuan pinjam {req.asset_name}", "", target="asset",
        )
        return req

    async def review_request(self, user: CurrentUser, request_id: UUID, data: LoanRequestReview) -> Any:
        reviewer = await self._own_employee(user)
        req = await self.repo.request_for_update(request_id)
        if req is None:
            raise NotFoundError("Pengajuan pinjam aset")
        if req.status != "PENDING":
            raise AppError("ALREADY_DECIDED", "Pengajuan ini sudah diputuskan.", status=409)
        if str(req.employee_id) == str(reviewer):
            raise ForbiddenError("Pemohon tidak dapat menyetujui pengajuannya sendiri.")
        note = data.note.strip() if data.note else None
        assignment_id: UUID | None = None
        if data.decision == "APPROVED":
            loan = await self.lend(LoanCreate(
                asset_type=req.asset_type, tool_id=req.tool_id, vehicle_id=req.vehicle_id,
                employee_id=req.employee_id,
            ))
            assignment_id = loan.assignment_id
        await self.repo.set_request_status(request_id, data.decision, str(reviewer), note, assignment_id)
        result = await self.repo.get_request(request_id)
        verdict = "disetujui, silakan ambil aset" if data.decision == "APPROVED" else "ditolak"
        await self._notify().notify_employees(
            [result.employee_id], "ASSET_REQUEST_DECIDED", f"Pengajuan pinjam {result.asset_name} {verdict}",
            note or "", target="asset",
        )
        return result

    async def request_return(self, user: CurrentUser, assignment_id: UUID, data: LoanReturnRequest) -> Any:
        employee_id = await self._own_employee(user)
        loan = await self.repo.get_loan(assignment_id)
        if loan is None:
            raise NotFoundError("Peminjaman aset")
        if str(loan.employee_id) != str(employee_id):
            raise ForbiddenError("Hanya pemegang aset yang dapat mengajukan pengembalian.")
        if loan.returned_at is not None:
            raise AppError("ALREADY_RETURNED", "Aset ini sudah dikembalikan.", status=409)
        photo = await self._path(data.photo_file_id, "foto kondisi pengembalian")
        assert photo is not None
        note = data.note.strip() if data.note else None
        await self.repo.request_return(assignment_id, data.condition, note, photo)
        done = await self.repo.get_loan(assignment_id)
        await self._notify().notify_roles(
            ["ADMIN_HR_GA"], "ASSET_RETURN_REQUESTED",
            f"{done.employee_name} mengembalikan {done.asset_name}, mohon diperiksa", note or "", target="asset",
        )
        return done
