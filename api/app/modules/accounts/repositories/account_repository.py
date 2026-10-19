"""
app/modules/accounts/repositories/account_repository.py

Repository akses data akun karyawan dan status autentikasinya.
"""
from app.modules.auth.repositories.auth_user_repository import AuthUserRepository


class AccountRepository(AuthUserRepository):
    """Repository persistensi data akun login karyawan."""
