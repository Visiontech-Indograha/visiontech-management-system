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
    """
    Fungsi pembantu untuk memetakan data row dari database ke skema AccountOut.

    Args:
        row (Any): Data akun dari database.

    Returns:
        AccountOut: Skema balikan detail akun.
    """
    if row is None:
        return AccountOut(exists=False)
    return AccountOut(exists=True, user_id=row.id, login=str(row.login), is_active=row.is_active,
                      last_login_at=row.last_login_at, failed_logins=getattr(row, "failures", None) or 0,
                      locked_until=getattr(row, "locked_until", None))


@router.get("", response_model=AccountOut)
async def get_account(emp_id: UUID, current_user: CurrentUser = _manager, account_service: AccountService = Depends(get_account_service)) -> AccountOut:
    """
    Mendapatkan detail akun berdasarkan ID karyawan.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Detail akun (AccountOut)
    """
    # Menggunakan injeksi dependensi untuk mendapatkan AccountService
    # Memanggil service layer account untuk mengambil akun berdasarkan organisasi pengguna saat ini
    return _out(await account_service.account(emp_id, current_user.organization_id))


@router.post("", response_model=AccountWithPassword, status_code=status.HTTP_201_CREATED)
async def create_account(emp_id: UUID, data: AccountCreate, current_user: CurrentUser = _manager,
                         account_service: AccountService = Depends(get_account_service)) -> AccountWithPassword:
    """
    Membuat akun baru untuk karyawan. Password sementara dikembalikan SEKALI — sampaikan ke karyawan, minta diganti setelah masuk.

    Path params:
    - emp_id: UUID dari karyawan

    Body params:
    - data: Data akun baru yang akan dibuat

    Return: Akun yang dibuat beserta password sementara (AccountWithPassword)
    """
    # Menggunakan AccountService yang di-inject via Depends
    # Meneruskan data akun ke layer service untuk dibuat di database
    row, password = await account_service.create(emp_id, current_user.organization_id, data.login.strip().lower())
    return AccountWithPassword(**_out(row).model_dump(), temporary_password=password)


@router.post("/reset-password", response_model=AccountWithPassword)
async def reset_password(emp_id: UUID, current_user: CurrentUser = _manager,
                         account_service: AccountService = Depends(get_account_service)) -> AccountWithPassword:
    """
    Mereset password akun. Password sementara baru; semua sesi akun itu dicabut.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Detail akun beserta password sementara yang baru (AccountWithPassword)
    """
    # Injeksi AccountService untuk operasi reset password
    # Meneruskan perintah reset password ke service layer
    row, password = await account_service.reset_password(emp_id, current_user.organization_id)
    return AccountWithPassword(**_out(row).model_dump(), temporary_password=password)


@router.post("/deactivate", response_model=AccountOut)
async def deactivate(emp_id: UUID, current_user: CurrentUser = _manager, account_service: AccountService = Depends(get_account_service)) -> AccountOut:
    """
    Menonaktifkan akun karyawan.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Detail akun yang baru saja dinonaktifkan (AccountOut)
    """
    # Mengambil instance AccountService melalui injeksi dependensi
    # Meneruskan status nonaktif (False) ke layer service
    return _out(await account_service.set_active(emp_id, current_user.organization_id, False))


@router.post("/activate", response_model=AccountOut)
async def activate(emp_id: UUID, current_user: CurrentUser = _manager, account_service: AccountService = Depends(get_account_service)) -> AccountOut:
    """
    Mengaktifkan kembali akun karyawan.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Detail akun yang baru saja diaktifkan (AccountOut)
    """
    # Menggunakan dependensi service untuk menangani pengaturan status akun
    # Meneruskan status aktif (True) ke service layer
    return _out(await account_service.set_active(emp_id, current_user.organization_id, True))
