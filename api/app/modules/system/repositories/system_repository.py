"""
app/modules/system/repositories/system_repository.py

Repositori data sistem (sinkronisasi luring, pemantauan timeline, dan metadata berkas).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §5.5.
"""

from app.crud.crud_file import CRUDFile
from app.crud.crud_file_access import CRUDFileAccess
from app.crud.crud_monitoring import CRUDMonitoring
from app.crud.crud_sync import CRUDSync


class SyncRepository(CRUDSync):
    """Repositori log dan antrean sinkronisasi luring."""


class MonitoringRepository(CRUDMonitoring):
    """Repositori agregasi lini masa dan rekap absensi organisasi."""


class FileRepository(CRUDFile):
    """Repositori metadata dan pendaftaran berkas."""


class FileAccessRepository(CRUDFileAccess):
    """Repositori pemeriksaan otorisasi akses berkas."""


__all__ = [
    "FileAccessRepository",
    "FileRepository",
    "MonitoringRepository",
    "SyncRepository",
]
