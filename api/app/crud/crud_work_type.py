"""
app/crud/crud_work_type.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.work_types.repositories.work_type_repository import (
    CRUDWorkType,
    WorkTypeRepository,
)

__all__ = ["CRUDWorkType", "WorkTypeRepository"]
