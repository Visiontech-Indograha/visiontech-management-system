"""
app/services/work_type_service.py
Shim re-export untuk kompatibilitas uji lama.
"""
from app.modules.work_types.services.work_type_service import WorkTypeService

__all__ = ["WorkTypeService"]
