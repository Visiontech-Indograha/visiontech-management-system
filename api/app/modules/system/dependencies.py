"""
app/modules/system/dependencies.py

Perakitan service modul system untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user, get_file_viewer_db
from app.core.config import settings
from app.modules.system.repositories.file_repository import CRUDFile
from app.modules.system.services.app_release_service import AppReleaseService
from app.modules.system.services.file_service import FileService
from app.modules.system.services.monitoring_service import MonitoringService
from app.modules.system.services.sync_service import SyncService


def get_file_service(db: AsyncSession = Depends(get_db_with_user)) -> FileService:
    return FileService(CRUDFile(db))


def get_file_viewer_service(db: AsyncSession = Depends(get_file_viewer_db)) -> FileService:
    return FileService(CRUDFile(db))


def get_monitoring_service(db: AsyncSession = Depends(get_db_with_user)) -> MonitoringService:
    return MonitoringService(db)


def get_sync_service(db: AsyncSession = Depends(get_db_with_user)) -> SyncService:
    return SyncService(db)


def get_app_release_service() -> AppReleaseService:
    """Rilis APK dibaca dari folder berkas (publik, tanpa sesi DB) — docs/32."""
    return AppReleaseService(settings.APP_RELEASE_DIR)
