"""
app/schemas/asset.py

Request and response schemas for assets and their allocations.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AssetCreate(BaseModel):
    """
    Schema for creating a new asset.
    """
    # Kategori aset, wajib dipilih dari enum DB (kendaraan atau perkakas)
    kind: Literal["VEHICLE", "TOOL"]
    vehicle_type: str | None = None
    code: str
    name: str
    condition: str = "Baik"


class AssetResponse(AssetCreate):
    """
    Schema for asset responses, adding system properties like ID and status.
    """
    id: UUID
    status: str


class AssetListItem(AssetResponse):
    """
    Schema for an asset listed with its current allocation and pending return requests.
    Aset + alokasi berjalan + pengajuan pengembalian yang menunggu (R-19, M6).
    """
    allocation_id: UUID | None = None
    work_plan_id: UUID | None = None
    plan_number: str | None = None
    leader_employee_id: UUID | None = None
    pending_return_id: UUID | None = None
    return_condition: str | None = None
    return_note: str | None = None
    return_requested_by_name: str | None = None


class PlanAssetItem(BaseModel):
    """
    Schema for an asset associated with a specific work plan.
    """
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
    # Alur SK v2: tombol "Kembalikan" di HP ketua
    allocation_id: UUID | None = None
    asset_status: str | None = None


class AssetReturnHistoryItem(BaseModel):
    """
    Schema representing the historical record of an asset return.
    """
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
    """
    Schema for requesting to reserve an asset.
    """
    work_plan_id: UUID
    driver_employee_id: UUID | None = None


class AssetReleaseRequest(BaseModel):
    """
    Schema for requesting to release a reserved asset.
    """
    work_plan_id: UUID


class AssetCheckRequest(BaseModel):
    """
    Schema for asset return check decision.
    """
    decision: Literal["ACCEPT", "APPEAL"]
    reason: str | None = None


class AssetStatusResponse(BaseModel):
    """
    Schema for reporting an asset's status.
    """
    asset_id: UUID
    status: str


class AssetAllocationResponse(BaseModel):
    """
    Schema detailing a specific asset allocation to a work plan.
    """
    id: UUID
    asset_id: UUID
    work_plan_id: UUID
    driver_employee_id: UUID | None
    allocated_by: UUID
    allocated_at: datetime
    released_at: datetime | None


class AssetReturnCreate(BaseModel):
    """
    Schema for requesting an asset return.
    """
    condition_on_return: str
    note: str | None = None


class AssetReturnVerify(BaseModel):
    """
    Schema for verifying and accepting or rejecting an asset return.
    """
    is_accepted: bool
    note: str | None = None


class AssetReturnResponse(BaseModel):
    """
    Schema detailing the outcome of an asset return process.
    """
    id: UUID
    asset_allocation_id: UUID
    requested_by: UUID
    requested_at: datetime
    verified_by: UUID | None
    verified_at: datetime | None
    condition_on_return: str | None
    is_accepted: bool | None
