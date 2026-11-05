"""Perakitan service penugasan peran untuk FastAPI `Depends` (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.role_assignments.repositories.role_assignment_repository import RoleAssignmentRepository
from app.modules.role_assignments.services.role_assignment_service import RoleAssignmentService


def get_role_assignment_service(db: AsyncSession = Depends(get_db_with_user)) -> RoleAssignmentService:
    return RoleAssignmentService(RoleAssignmentRepository(db))
