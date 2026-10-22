"""
app/modules/assets/controllers/asset_controller.py

Controller orkestrasi use case inventaris & peminjaman aset.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.assets.dependencies import get_asset_service
from app.modules.assets.schemas.asset_schema import (
    InspectionCreate,
    InspectionOut,
    LoanCreate,
    LoanOut,
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
    async def handle_list_tools(self, office_id: UUID | None, status: str | None) -> list[ToolOut]:
        return [ToolOut(**r._mapping) for r in await self.service.list_tools(office_id, status)]

    async def handle_create_tool(self, data: ToolCreate) -> ToolOut:
        return ToolOut(**(await self.service.create_tool(data))._mapping)

    async def handle_update_tool(self, tool_id: UUID, data: ToolUpdate) -> ToolOut:
        return ToolOut(**(await self.service.update_tool(tool_id, data))._mapping)

    async def handle_tool_status(self, tool_id: UUID, status: str) -> ToolOut:
        return ToolOut(**(await self.service.set_status("TOOL", tool_id, status))._mapping)

    # Kendaraan
    async def handle_list_vehicles(self, office_id: UUID | None, status: str | None) -> list[VehicleOut]:
        return [VehicleOut(**r._mapping) for r in await self.service.list_vehicles(office_id, status)]

    async def handle_create_vehicle(self, data: VehicleCreate) -> VehicleOut:
        return VehicleOut(**(await self.service.create_vehicle(data))._mapping)

    async def handle_update_vehicle(self, vehicle_id: UUID, data: VehicleUpdate) -> VehicleOut:
        return VehicleOut(**(await self.service.update_vehicle(vehicle_id, data))._mapping)

    async def handle_vehicle_status(self, vehicle_id: UUID, status: str) -> VehicleOut:
        return VehicleOut(**(await self.service.set_status("VEHICLE", vehicle_id, status))._mapping)

    async def handle_delete(self, asset_type: str, asset_id: UUID) -> dict[str, str]:
        await self.service.delete(asset_type, asset_id)
        return {"message": "Aset dihapus."}

    # Berkas & inspeksi kendaraan
    async def handle_vehicle_files(self, vehicle_id: UUID) -> list[VehicleFileOut]:
        return [VehicleFileOut(**r._mapping) for r in await self.service.vehicle_files(vehicle_id)]

    async def handle_add_vehicle_file(self, vehicle_id: UUID, data: VehicleFileCreate) -> list[VehicleFileOut]:
        return [VehicleFileOut(**r._mapping) for r in await self.service.add_vehicle_file(vehicle_id, data)]

    async def handle_inspections(self, vehicle_id: UUID) -> list[InspectionOut]:
        return [InspectionOut(**r._mapping) for r in await self.service.inspections(vehicle_id)]

    async def handle_add_inspection(
        self, user: CurrentUser, vehicle_id: UUID, data: InspectionCreate
    ) -> list[InspectionOut]:
        return [InspectionOut(**r._mapping) for r in await self.service.add_inspection(user, vehicle_id, data)]

    # Peminjaman
    async def handle_loans(
        self, user: CurrentUser, *, open_only: bool, employee_id: UUID | None, daily_plan_id: UUID | None
    ) -> list[LoanOut]:
        rows = await self.service.loans(user, open_only=open_only, employee_id=employee_id,
                                        daily_plan_id=daily_plan_id)
        return [LoanOut(**r._mapping) for r in rows]

    async def handle_lend(self, data: LoanCreate) -> LoanOut:
        return LoanOut(**(await self.service.lend(data))._mapping)

    async def handle_return(self, assignment_id: UUID, condition: str) -> LoanOut:
        return LoanOut(**(await self.service.return_loan(assignment_id, condition))._mapping)
