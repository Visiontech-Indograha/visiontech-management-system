from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class AssetCreate(BaseModel):
    kind: str
    vehicle_type: Optional[str] = None
    code: str
    name: str
    condition: str = "Baik"

class AssetResponse(AssetCreate):
    id: UUID
    status: str
    
class AssetAllocationCreate(BaseModel):
    asset_id: UUID
    work_plan_id: UUID
    driver_employee_id: Optional[UUID] = None

class AssetAllocationResponse(BaseModel):
    id: UUID
    asset_id: UUID
    work_plan_id: UUID
    driver_employee_id: Optional[UUID]
    allocated_by: UUID
    allocated_at: datetime
    released_at: Optional[datetime]

class AssetReturnCreate(BaseModel):
    condition_on_return: str
    note: Optional[str] = None

class AssetReturnVerify(BaseModel):
    is_accepted: bool
    note: Optional[str] = None

class AssetReturnResponse(BaseModel):
    id: UUID
    asset_allocation_id: UUID
    requested_by: UUID
    requested_at: datetime
    verified_by: Optional[UUID]
    verified_at: Optional[datetime]
    condition_on_return: Optional[str]
    is_accepted: Optional[bool]
