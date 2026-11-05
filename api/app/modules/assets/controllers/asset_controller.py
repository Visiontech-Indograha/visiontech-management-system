"""
app/modules/assets/controllers/asset_controller.py

Controller orkestrasi use case inventaris & peminjaman aset.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from datetime import date as _date
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.assets.dependencies import get_asset_service
from app.modules.assets.schemas.asset_schema import (
    AssetAvailabilityOut,
    InspectionCreate,
    InspectionOut,
    LoanCreate,
    LoanOut,
    LoanRequestCreate,
    LoanRequestOut,
    LoanRequestReview,
    LoanReturnRequest,
    ToolCreate,
    ToolOut,
    ToolUpdate,
    VehicleCreate,
    VehicleFileCreate,
    VehicleFileOut,
    VehicleOut,
    VehicleUpdate,
)
from app.modules.assets.services.asset_service import AssetService


class AssetController:
    """Controller alat, kendaraan, berkas/inspeksi kendaraan, dan peminjaman."""

    def __init__(self, asset_service: AssetService = Depends(get_asset_service)) -> None:
        self.service = asset_service

    # Alat
    async def handle_list_tools(
        self, office_id: UUID | None, status: str | None, user: CurrentUser
    ) -> list[ToolOut]:
        return [ToolOut(**r._mapping) for r in await self.service.list_tools(office_id, status, user)]

    async def handle_create_tool(self, data: ToolCreate, user: CurrentUser | None = None) -> ToolOut:
        return ToolOut(**(await self.service.create_tool(data, user))._mapping)

    async def handle_update_tool(self, tool_id: UUID, data: ToolUpdate, user: CurrentUser | None = None) -> ToolOut:
        return ToolOut(**(await self.service.update_tool(tool_id, data, user))._mapping)

    async def handle_tool_status(self, tool_id: UUID, status: str, user: CurrentUser | None = None) -> ToolOut:
        return ToolOut(**(await self.service.set_status("TOOL", tool_id, status, user))._mapping)

    # Kendaraan
    async def handle_list_vehicles(
        self, office_id: UUID | None, status: str | None, user: CurrentUser
    ) -> list[VehicleOut]:
        return [VehicleOut(**r._mapping) for r in await self.service.list_vehicles(office_id, status, user)]

    async def handle_create_vehicle(self, data: VehicleCreate, user: CurrentUser | None = None) -> VehicleOut:
        return VehicleOut(**(await self.service.create_vehicle(data, user))._mapping)

    async def handle_update_vehicle(
        self, vehicle_id: UUID, data: VehicleUpdate, user: CurrentUser | None = None
    ) -> VehicleOut:
        return VehicleOut(**(await self.service.update_vehicle(vehicle_id, data, user))._mapping)

    async def handle_vehicle_status(self, vehicle_id: UUID, status: str, user: CurrentUser | None = None) -> VehicleOut:
        return VehicleOut(**(await self.service.set_status("VEHICLE", vehicle_id, status, user))._mapping)

    async def handle_delete(self, asset_type: str, asset_id: UUID, user: CurrentUser | None = None) -> dict[str, str]:
        await self.service.delete(asset_type, asset_id, user)
        return {"message": "Aset dihapus."}

    # Berkas & inspeksi kendaraan
    async def handle_vehicle_files(self, user: CurrentUser, vehicle_id: UUID) -> list[VehicleFileOut]:
        return [VehicleFileOut(**r._mapping) for r in await self.service.vehicle_files(vehicle_id, user)]

    async def handle_add_vehicle_file(
        self, vehicle_id: UUID, data: VehicleFileCreate, user: CurrentUser | None = None
    ) -> list[VehicleFileOut]:
        return [VehicleFileOut(**r._mapping) for r in await self.service.add_vehicle_file(vehicle_id, data, user)]

    async def handle_inspections(self, user: CurrentUser, vehicle_id: UUID) -> list[InspectionOut]:
        return [InspectionOut(**r._mapping) for r in await self.service.inspections(vehicle_id, user)]

    async def handle_add_inspection(
        self, user: CurrentUser, vehicle_id: UUID, data: InspectionCreate
    ) -> list[InspectionOut]:
        return [InspectionOut(**r._mapping) for r in await self.service.add_inspection(user, vehicle_id, data)]

    async def handle_availability(
        self, work_date: _date, team_id: UUID | None, user: CurrentUser
    ) -> list[AssetAvailabilityOut]:
        return [AssetAvailabilityOut(**r) for r in await self.service.availability(work_date, team_id, user)]

    # Peminjaman
    async def handle_loans(
        self, user: CurrentUser, *, open_only: bool, employee_id: UUID | None, daily_plan_id: UUID | None
    ) -> list[LoanOut]:
        rows = await self.service.loans(user, open_only=open_only, employee_id=employee_id,
                                        daily_plan_id=daily_plan_id)
        return [LoanOut(**r._mapping) for r in rows]

    async def handle_lend(self, data: LoanCreate, user: CurrentUser | None = None) -> LoanOut:
        return LoanOut(**(await self.service.lend(data, user))._mapping)

    async def handle_return(self, assignment_id: UUID, condition: str, user: CurrentUser | None = None) -> LoanOut:
        return LoanOut(**(await self.service.return_loan(assignment_id, condition, user))._mapping)

    # Pengajuan pinjam & pengembalian
    async def handle_request_loan(self, user: CurrentUser, data: LoanRequestCreate) -> LoanRequestOut:
        return LoanRequestOut(**(await self.service.request_loan(user, data))._mapping)

    async def handle_requests(self, user: CurrentUser, status: str | None) -> list[LoanRequestOut]:
        return [LoanRequestOut(**r._mapping) for r in await self.service.requests(user, status=status)]

    async def handle_cancel_request(self, user: CurrentUser, request_id: UUID) -> LoanRequestOut:
        return LoanRequestOut(**(await self.service.cancel_request(user, request_id))._mapping)

    async def handle_review_request(
        self, user: CurrentUser, request_id: UUID, data: LoanRequestReview
    ) -> LoanRequestOut:
        return LoanRequestOut(**(await self.service.review_request(user, request_id, data))._mapping)

    async def handle_return_request(
        self, user: CurrentUser, assignment_id: UUID, data: LoanReturnRequest
    ) -> LoanOut:
        return LoanOut(**(await self.service.request_return(user, assignment_id, data))._mapping)
