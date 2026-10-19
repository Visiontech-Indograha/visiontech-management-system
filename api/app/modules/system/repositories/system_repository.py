"""
app/modules/system/repositories/system_repository.py
"""
from app.crud.crud_file_access import CRUDFileAccess
from app.crud.crud_monitoring import CRUDMonitoring

from .file_repository import CRUDFile, FileRepository
from .sync_repository import CRUDSync, SyncRepository


class FileAccessRepository(CRUDFileAccess):
    pass

class MonitoringRepository(CRUDMonitoring):
    pass

__all__ = [
    "CRUDFile",
    "CRUDSync",
    "FileAccessRepository",
    "FileRepository",
    "MonitoringRepository",
    "SyncRepository",
]
