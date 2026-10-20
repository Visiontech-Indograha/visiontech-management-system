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
"""
from __future__ import annotations

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
    ToolCreate,
    ToolUpdate,
    VehicleCreate,
    VehicleFileCreate,
    VehicleUpdate,
)

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


class AssetService:
    """Use case inventaris & peminjaman aset."""

    def __init__(self, repo: AssetRepository) -> None:
        self.repo = repo

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
    async def loans(
        self, user: CurrentUser, *, open_only: bool, employee_id: UUID | None, daily_plan_id: UUID | None
    ) -> list[Any]:
        """Pengelola aset & peran kantor (view:teams) melihat semua; anggota tim melihat aset jadwal timnya;
        selain itu hanya pinjaman miliknya sendiri."""
        if not ({Permission.MANAGE_ASSETS.value, Permission.VIEW_TEAMS.value} & set(user.permissions)):
            own = await self.repo.employee_of_user(user.user_id)
            if own is None:
                return []
            plan = await self.repo.plan_for_loan(daily_plan_id, own) if daily_plan_id else None
            if plan is None or not plan.on_team:
                employee_id = UUID(own)
        return await self.repo.loans(open_only=open_only, employee_id=employee_id, daily_plan_id=daily_plan_id)

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
        if asset.status != "ready" or await self.repo.has_open_loan(data.asset_type, asset_id):
            raise AppError("ASSET_NOT_AVAILABLE", f"{_LABEL[data.asset_type]} tidak siap dipinjam.", status=409)
        if not await self.repo.employee_active(data.employee_id):
            raise ValidationError("Karyawan tidak ditemukan, nonaktif, atau sedang proses offboarding.")

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
        return await self.repo.get_loan(assignment_id)
