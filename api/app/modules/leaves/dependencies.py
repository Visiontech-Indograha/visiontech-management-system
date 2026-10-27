"""
app/modules/leaves/dependencies.py

Dependency injection untuk modul leaves.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.leaves.repositories.leave_repository import LeaveRepository
from app.modules.leaves.services.leave_service import LeaveService


def get_leave_repository(db: AsyncSession = Depends(get_db_with_user)) -> LeaveRepository:
    return LeaveRepository(db)


def get_leave_service(repo: LeaveRepository = Depends(get_leave_repository)) -> LeaveService:
    return LeaveService(repo)
