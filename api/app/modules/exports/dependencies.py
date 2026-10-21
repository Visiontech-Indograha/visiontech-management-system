"""
app/modules/exports/dependencies.py

Perakitan service modul exports. Akses order lewat API publik modul work_completion (sesi yang sama = satu transaksi).
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, get_db
from app.modules.exports.repositories.export_repository import ExportRepository
from app.modules.exports.services.export_service import ExportService
from app.modules.work_completion.dependencies import get_work_completion_service
from app.modules.work_completion.services.work_completion_service import WorkCompletionService


def get_export_service(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    orders: WorkCompletionService = Depends(get_work_completion_service),
) -> ExportService:
    return ExportService(ExportRepository(db), orders)
