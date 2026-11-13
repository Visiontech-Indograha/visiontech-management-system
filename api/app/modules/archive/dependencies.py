"""Perakitan service modul archive (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.archive.repositories.archive_repository import ArchiveRepository
from app.modules.archive.services.archive_service import ArchiveService


def get_archive_service(db: AsyncSession = Depends(get_db_with_user)) -> ArchiveService:
    return ArchiveService(ArchiveRepository(db))
