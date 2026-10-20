"""
app/modules/system/repositories/system_repository.py
"""
from app.modules.system.repositories.monitoring_repository import CRUDMonitoring
from app.shared.access.file_access_repository import CRUDFileAccess

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
