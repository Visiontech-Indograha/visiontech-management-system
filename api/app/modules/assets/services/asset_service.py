"""
app/modules/assets/services/asset_service.py

Layanan logika bisnis untuk modul aset dan peminjaman/pengembalian kerja.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""
from app.services.asset_reservation_service import (
    AssetReservationService as BaseAssetReservationService,
)


class AssetReservationService(BaseAssetReservationService):
    """
    Layanan bisnis reservasi aset.
    Mengelola aturan pemesanan aset SK, verifikasi pengemudi, inspeksi kelayakan, dan penyelesaian BAST.
    """


__all__ = ["AssetReservationService"]
