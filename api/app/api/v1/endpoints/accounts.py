"""
Akun login karyawan (M1-01, R-20). Tipis: izin manage:users di sini, aturan di services/account_service.py.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_account_service, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.account import AccountCreate, AccountOut, AccountWithPassword
from app.services.account_service import AccountService

router = APIRouter(prefix="/employees/{emp_id}/account", tags=["Employee Account"])

_manager = Depends(require_permission(Permission.MANAGE_USERS))
_db = Depends(get_db_with_user)








def _out(row: Any) -> AccountOut:
    if row is None:
        return AccountOut(exists=False)
    return AccountOut(exists=True, user_id=row.id, login=str(row.login), is_active=row.is_active,
                      last_login_at=row.last_login_at, failed_logins=getattr(row, "failures", None) or 0,
                      locked_until=getattr(row, "locked_until", None))


@router.get("", response_model=AccountOut)
async def get_account(emp_id: UUID, current_user: CurrentUser = _manager, account_service: AccountService = Depends(get_account_service)) -> AccountOut:
    return _out(await account_service.account(emp_id, current_user.organization_id))


@router.post("", response_model=AccountWithPassword, status_code=status.HTTP_201_CREATED)
async def create_account(emp_id: UUID, data: AccountCreate, current_user: CurrentUser = _manager,
                         account_service: AccountService = Depends(get_account_service)) -> AccountWithPassword:
    """Password sementara dikembalikan SEKALI — sampaikan ke karyawan, minta diganti setelah masuk."""
    row, password = await account_service.create(emp_id, current_user.organization_id, data.login.strip().lower())
    return AccountWithPassword(**_out(row).model_dump(), temporary_password=password)


@router.post("/reset-password", response_model=AccountWithPassword)
async def reset_password(emp_id: UUID, current_user: CurrentUser = _manager,
                         account_service: AccountService = Depends(get_account_service)) -> AccountWithPassword:
    """Password sementara baru; semua sesi akun itu dicabut."""
    row, password = await account_service.reset_password(emp_id, current_user.organization_id)
    return AccountWithPassword(**_out(row).model_dump(), temporary_password=password)


@router.post("/deactivate", response_model=AccountOut)
async def deactivate(emp_id: UUID, current_user: CurrentUser = _manager, account_service: AccountService = Depends(get_account_service)) -> AccountOut:
    return _out(await account_service.set_active(emp_id, current_user.organization_id, False))


@router.post("/activate", response_model=AccountOut)
async def activate(emp_id: UUID, current_user: CurrentUser = _manager, account_service: AccountService = Depends(get_account_service)) -> AccountOut:
    return _out(await account_service.set_active(emp_id, current_user.organization_id, True))
