"""
app/modules/auth/repositories/auth_user_repository.py

Repository akses data persistensi untuk entitas pengguna (vms.app_user) dan perannya.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.4.
"""

from app.crud.crud_user import CRUDUser


class AuthUserRepository(CRUDUser):
    """
    Repository akses data pengguna vms.app_user dan peran globalnya.
    Menyediakan query find_by_login, find_by_id, find_identity, update_password, dsb.
    """
