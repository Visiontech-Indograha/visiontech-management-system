"""
app/modules/assets/schemas/asset_schema.py

Skema validasi permintaan dan respons manajemen aset dan alokasi kerja.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.4.
"""
from app.schemas.asset import (
    AssetAllocationResponse,
    AssetCheckRequest,
    AssetCreate,
    AssetListItem,
    AssetReleaseRequest,
    AssetReserveRequest,
    AssetResponse,
    AssetReturnCreate,
    AssetReturnHistoryItem,
    AssetReturnResponse,
    AssetReturnVerify,
    AssetStatusResponse,
    PlanAssetItem,
)

__all__ = [
    "AssetAllocationResponse",
    "AssetCheckRequest",
    "AssetCreate",
    "AssetListItem",
    "AssetReleaseRequest",
    "AssetReserveRequest",
    "AssetResponse",
    "AssetReturnCreate",
    "AssetReturnHistoryItem",
    "AssetReturnResponse",
    "AssetReturnVerify",
    "AssetStatusResponse",
    "PlanAssetItem",
]
