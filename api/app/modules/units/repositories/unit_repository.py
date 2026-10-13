"""
app/modules/units/repositories/unit_repository.py

Repository akses data persistensi untuk unit organisasi.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.4.
"""
from app.crud.crud_unit import CRUDUnit


class UnitRepository(CRUDUnit):
    """
    Repository akses data tabel vms.unit.
    """

