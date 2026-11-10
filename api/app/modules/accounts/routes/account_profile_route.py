"""
app/modules/accounts/routes/account_profile_route.py

Rute endpoint HTTP untuk akun login karyawan (/employees/{emp_id}/account).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission, require_permission_for_employee
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.accounts.controllers.account_profile_controller import AccountProfileController
from app.modules.accounts.schemas.account_schema import (
    AccountCreate,
    AccountLoginUpdate,
    AccountOut,
    AccountRoleUpdate,
    AccountSessionsRevoked,
    AccountWithPassword,
)
from app.modules.auth.schemas.auth_session_schema import AuthSessionResponseSchema

router = APIRouter(prefix="/employees/{emp_id}/account", tags=["Employee Account"])

_manager = Depends(require_permission_for_employee(Permission.MANAGE_USERS, "emp_id"))
_delete_any = Depends(require_permission(Permission.DELETE_ANY))


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
    Membuat akun baru untuk karyawan dengan kata sandi sementara. Peran lapangan (EMPLOYEE/TEAM_LEADER) opsional;
    hanya HR/SUPER_ADMIN.
    """
    return await controller.handle_create_account(emp_id, current_user, data)


@router.post("/role", response_model=AccountOut)
async def set_field_role(
    emp_id: UUID,
    data: AccountRoleUpdate,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountOut:
    """
    Mengubah peran utama akun. HR/SUPER_ADMIN: EMPLOYEE/TEAM_LEADER; peran OM/PM/HSE/HR/FINANCE hanya SUPER_ADMIN
    (bukan diri sendiri, bukan SUPER_ADMIN). Sesi dicabut; tercatat di audit.
    """
    return await controller.handle_set_role(emp_id, current_user, data)


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


@router.delete("")
async def delete_account(
    emp_id: UUID,
    current_user: CurrentUser = _delete_any,
    controller: AccountProfileController = Depends(),
) -> dict[str, str]:
    """Hapus permanen akun login karyawan — hanya SUPER_ADMIN."""
    return await controller.handle_delete_account(emp_id, current_user)


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


@router.get("/sessions", response_model=list[AuthSessionResponseSchema])
async def list_sessions(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> list[AuthSessionResponseSchema]:
    """Perangkat yang sedang masuk dengan akun karyawan ini (HR/admin)."""
    return await controller.handle_list_sessions(emp_id, current_user.organization_id)


@router.post("/sessions/revoke-all", response_model=AccountSessionsRevoked)
async def revoke_all_sessions(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountSessionsRevoked:
    """Paksa keluar semua perangkat akun karyawan; tercatat di audit."""
    return await controller.handle_revoke_all_sessions(emp_id, current_user)


@router.post("/sessions/{session_id}/revoke", response_model=AccountSessionsRevoked)
async def revoke_session(
    emp_id: UUID,
    session_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountSessionsRevoked:
    """Cabut satu perangkat akun karyawan; sesi milik akun lain → 404."""
    return await controller.handle_revoke_session(emp_id, session_id, current_user)


@router.post("/device-slots/reset", response_model=AccountSessionsRevoked)
async def reset_device_slots(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountSessionsRevoked:
    """Kosongkan slot perangkat akun (batas perangkat per akun) dengan mencabut semua sesinya; tercatat di audit."""
    return await controller.handle_reset_device_slots(emp_id, current_user)


@router.post("/unlock", response_model=AccountOut)
async def unlock(
    emp_id: UUID,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountOut:
    """Buka kunci akun yang terkunci karena gagal masuk berulang; tercatat di audit."""
    return await controller.handle_unlock(emp_id, current_user)


@router.post("/login", response_model=AccountOut)
async def change_login(
    emp_id: UUID,
    data: AccountLoginUpdate,
    current_user: CurrentUser = _manager,
    controller: AccountProfileController = Depends(),
) -> AccountOut:
    """Ganti email login akun (unik); sesi lama dicabut; tercatat di audit."""
    return await controller.handle_change_login(emp_id, current_user, data)
