"""
app/modules/assets/repositories/asset_repository.py

Repositori data aset, alokasi penggunaan, dan pengembalian BAST.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""

from app.crud.crud_asset_reservation import CRUDAssetReservation


class AssetRepository(CRUDAssetReservation):
    """
    Repositori akses data master aset, status alokasi SK, pemeriksaan kelayakan, dan BAST pengembalian.
    """
