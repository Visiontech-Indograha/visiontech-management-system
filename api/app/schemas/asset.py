from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AssetCreate(BaseModel):
    kind: str
    vehicle_type: str | None = None
    code: str
    name: str
    condition: str = "Baik"

class AssetResponse(AssetCreate):
    id: UUID
    status: str
    
class AssetReserveRequest(BaseModel):
    work_plan_id: UUID
    driver_employee_id: UUID | None = None


class AssetReleaseRequest(BaseModel):
    work_plan_id: UUID


class AssetCheckRequest(BaseModel):
    decision: str            # ACCEPT | APPEAL
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
