"""
app/crud/crud_overtime.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.overtime.repositories.overtime_repository import (
    CRUDOvertime,
    OvertimeRepository,
)

__all__ = ["CRUDOvertime", "OvertimeRepository"]
