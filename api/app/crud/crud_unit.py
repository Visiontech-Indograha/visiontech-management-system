"""
app/crud/crud_unit.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.units.repositories.unit_repository import CRUDUnit, UnitRepository

__all__ = ["CRUDUnit", "UnitRepository"]
