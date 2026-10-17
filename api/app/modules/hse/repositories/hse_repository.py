"""
app/modules/hse/repositories/hse_repository.py

Repositori data insiden K3 (HSE) dan laporan harian kerja.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""

from app.crud.crud_hse import CRUDHse


class HseRepository(CRUDHse):
    """
    Repositori akses data insiden K3, bukti insiden, laporan harian tim, dan centang tugas harian.
    """
