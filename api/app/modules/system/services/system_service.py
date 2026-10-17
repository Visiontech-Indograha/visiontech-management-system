"""
app/modules/system/services/system_service.py

Layanan logika bisnis untuk modul sistem (rilis aplikasi, sinkronisasi, pemantauan, pengelolaan berkas).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.3.
"""

from app.services.app_release_service import (
    FILES_PATH,
)
from app.services.app_release_service import (
    AppReleaseService as BaseAppReleaseService,
)
from app.services.file_service import FileService as BaseFileService
from app.services.monitoring_service import (
    MonitoringService as BaseMonitoringService,
)
from app.services.sync_service import SyncService as BaseSyncService


class AppReleaseService(BaseAppReleaseService):
    """Layanan resolusi pembaruan dan rilis aplikasi Android."""


class SyncService(BaseSyncService):
    """Layanan orkestrasi operasi sinkronisasi data luring."""


class MonitoringService(BaseMonitoringService):
    """Layanan lini masa dan rekap analitik pemantauan."""


class FileService(BaseFileService):
    """Layanan pendaftaran berkas, deduplikasi, dan otorisasi penyimpanan MinIO."""


__all__ = [
    "FILES_PATH",
    "AppReleaseService",
    "FileService",
    "MonitoringService",
    "SyncService",
]
