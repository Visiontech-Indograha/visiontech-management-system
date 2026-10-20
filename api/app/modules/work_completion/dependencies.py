"""
app/modules/work_completion/dependencies.py

Perakitan service modul work_completion untuk FastAPI `Depends`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, get_db
from app.modules.work_completion.repositories.work_completion_repository import CRUDWorkCompletion
from app.modules.work_completion.services.work_completion_service import WorkCompletionService


def get_work_completion_service(db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> WorkCompletionService:
    """Dependency injector untuk WorkCompletionService."""
    return WorkCompletionService(CRUDWorkCompletion(db))
