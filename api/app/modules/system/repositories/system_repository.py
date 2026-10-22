"""
app/modules/system/repositories/system_repository.py
"""
from app.modules.system.repositories.monitoring_repository import CRUDMonitoring

from .file_repository import CRUDFile, FileRepository
from .sync_repository import CRUDSync, SyncRepository


class MonitoringRepository(CRUDMonitoring):
    pass

__all__ = [
    "CRUDFile",
    "CRUDSync",
    "FileRepository",
    "MonitoringRepository",
    "SyncRepository",
]
