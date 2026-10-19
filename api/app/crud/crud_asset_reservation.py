"""
app/crud/crud_asset_reservation.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.assets.repositories.asset_repository import (
    AssetRepository,
    CRUDAssetReservation,
)

__all__ = ["AssetRepository", "CRUDAssetReservation"]
