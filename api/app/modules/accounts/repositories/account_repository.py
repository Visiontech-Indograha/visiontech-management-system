"""
app/modules/accounts/repositories/account_repository.py

Repository akses data akun karyawan dan status autentikasinya.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.4.
"""

from app.crud.crud_user import CRUDUser


class AccountRepository(CRUDUser):
    """
    Repository persistensi data akun login karyawan.
    """
