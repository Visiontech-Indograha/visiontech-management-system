"""
app/modules/accounts/routes/account_profile_route.py

Rute endpoint HTTP untuk akun login karyawan (/employees/{emp_id}/account).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.accounts.controllers.account_profile_controller import AccountProfileController
from app.modules.accounts.schemas.account_schema import AccountCreate, AccountOut, AccountWithPassword

router = APIRouter(prefix="/employees/{emp_id}/account", tags=["Employee Account"])

_manager = Depends(require_permission(Permission.MANAGE_USERS))


@router.get("", response_model=AccountOut)
async def get_account(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountOut:
    """
    Mendapatkan detail akun berdasarkan ID karyawan.
    """
    return await controller.handle_get_account(emp_id, current_user.organization_id)


@router.post("", response_model=AccountWithPassword, status_code=status.HTTP_201_CREATED)
async def create_account(
    emp_id: UUID,
    data: AccountCreate,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountWithPassword:
    """
    Membuat akun baru untuk karyawan dengan kata sandi sementara.
    """
    return await controller.handle_create_account(emp_id, current_user.organization_id, data)


@router.post("/reset-password", response_model=AccountWithPassword)
async def reset_password(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountWithPassword:
    """
    Mereset password akun karyawan ke password sementara baru.
    """
    return await controller.handle_reset_password(emp_id, current_user.organization_id)


@router.post("/deactivate", response_model=AccountOut)
async def deactivate(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountOut:
    """
    Menonaktifkan akun karyawan.
    """
    return await controller.handle_deactivate(emp_id, current_user.organization_id)


@router.post("/activate", response_model=AccountOut)
async def activate(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountOut:
    """
    Mengaktifkan kembali akun karyawan.
    """
    return await controller.handle_activate(emp_id, current_user.organization_id)

