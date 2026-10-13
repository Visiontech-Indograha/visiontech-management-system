"""
app/modules/hse/services/hse_service.py

Layanan logika bisnis untuk modul insiden K3 (HSE) dan laporan harian kerja.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""
from app.services.hse_service import HseService as BaseHseService


class HseService(BaseHseService):
    """
    Layanan bisnis insiden K3 dan laporan harian tim kerja.
    Mengelola aturan pelaporan insiden, validasi tanggal pelaksanaan, dan penyerahan serta review laporan harian.
    """


__all__ = ["HseService"]
