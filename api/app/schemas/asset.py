from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AssetCreate(BaseModel):
    kind: Literal["VEHICLE", "TOOL"]  # enum DB asset_kind
    vehicle_type: str | None = None
    code: str
    name: str
    condition: str = "Baik"

class AssetResponse(AssetCreate):
    id: UUID
    status: str
    
class AssetListItem(AssetResponse):
    """Aset + alokasi berjalan + pengajuan pengembalian yang menunggu (R-19, M6)."""
    allocation_id: UUID | None = None
    work_plan_id: UUID | None = None
    plan_number: str | None = None
    leader_employee_id: UUID | None = None
    pending_return_id: UUID | None = None
    return_condition: str | None = None
    return_note: str | None = None
    return_requested_by_name: str | None = None


class PlanAssetItem(BaseModel):
    id: UUID
    name: str
    code: str
    kind: str
    vehicle_type: str | None
    driver_name: str | None
    allocated_at: datetime
    released_at: datetime | None
    returned_condition: str | None
    return_accepted: bool | None


class AssetReturnHistoryItem(BaseModel):
    id: UUID
    plan_number: str | None
    requested_by_name: str
    requested_at: datetime
    condition_on_return: str | None
    note: str | None
    verified_by_name: str | None
    verified_at: datetime | None
    is_accepted: bool | None


class AssetReserveRequest(BaseModel):
    work_plan_id: UUID
    driver_employee_id: UUID | None = None


class AssetReleaseRequest(BaseModel):
    work_plan_id: UUID


class AssetCheckRequest(BaseModel):
    decision: Literal["ACCEPT", "APPEAL"]
    reason: str | None = None


class AssetStatusResponse(BaseModel):
    asset_id: UUID
    status: str

class AssetAllocationResponse(BaseModel):
    id: UUID
    asset_id: UUID
    work_plan_id: UUID
    driver_employee_id: UUID | None
    allocated_by: UUID
    allocated_at: datetime
    released_at: datetime | None

class AssetReturnCreate(BaseModel):
    condition_on_return: str
    note: str | None = None

class AssetReturnVerify(BaseModel):
    is_accepted: bool
    note: str | None = None

class AssetReturnResponse(BaseModel):
    id: UUID
    asset_allocation_id: UUID
    requested_by: UUID
    requested_at: datetime
    verified_by: UUID | None
    verified_at: datetime | None
    condition_on_return: str | None
    is_accepted: bool | None
