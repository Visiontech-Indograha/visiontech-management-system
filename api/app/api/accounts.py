"""
Akun login karyawan (M1-01, R-20). Tipis: izin manage:users di sini, aturan di services/account_service.py.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.repositories.employee_repo import EmployeeRepo
from app.repositories.session_repo import SessionRepo
from app.repositories.user_repo import UserRepo
from app.services.account_service import AccountService

router = APIRouter(prefix="/employees/{emp_id}/account", tags=["Employee Account"])

_manager = Depends(require_permission(Permission.MANAGE_USERS))
_db = Depends(get_db_with_user)


class AccountOut(BaseModel):
    exists: bool
    user_id: UUID | None = None
    login: str | None = None
    is_active: bool | None = None
    last_login_at: datetime | None = None


class AccountCreate(BaseModel):
    login: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)


class AccountWithPassword(AccountOut):
    temporary_password: str


def _service(db: AsyncSession) -> AccountService:
    return AccountService(UserRepo(db), EmployeeRepo(db), SessionRepo(db))


def _out(row: Any) -> AccountOut:
    if row is None:
        return AccountOut(exists=False)
    return AccountOut(exists=True, user_id=row.id, login=str(row.login), is_active=row.is_active,
                      last_login_at=row.last_login_at)


@router.get("", response_model=AccountOut)
async def get_account(emp_id: UUID, current_user: CurrentUser = _manager, db: AsyncSession = _db) -> AccountOut:
    return _out(await _service(db).account(emp_id, current_user.organization_id))


@router.post("", response_model=AccountWithPassword, status_code=status.HTTP_201_CREATED)
async def create_account(emp_id: UUID, data: AccountCreate, current_user: CurrentUser = _manager,
                         db: AsyncSession = _db) -> AccountWithPassword:
    """Password sementara dikembalikan SEKALI — sampaikan ke karyawan, minta diganti setelah masuk."""
    row, password = await _service(db).create(emp_id, current_user.organization_id, data.login.strip().lower())
    return AccountWithPassword(**_out(row).model_dump(), temporary_password=password)


@router.post("/reset-password", response_model=AccountWithPassword)
async def reset_password(emp_id: UUID, current_user: CurrentUser = _manager,
                         db: AsyncSession = _db) -> AccountWithPassword:
    """Password sementara baru; semua sesi akun itu dicabut."""
    row, password = await _service(db).reset_password(emp_id, current_user.organization_id)
    return AccountWithPassword(**_out(row).model_dump(), temporary_password=password)


@router.post("/deactivate", response_model=AccountOut)
async def deactivate(emp_id: UUID, current_user: CurrentUser = _manager, db: AsyncSession = _db) -> AccountOut:
    return _out(await _service(db).set_active(emp_id, current_user.organization_id, False))


@router.post("/activate", response_model=AccountOut)
async def activate(emp_id: UUID, current_user: CurrentUser = _manager, db: AsyncSession = _db) -> AccountOut:
    return _out(await _service(db).set_active(emp_id, current_user.organization_id, True))
