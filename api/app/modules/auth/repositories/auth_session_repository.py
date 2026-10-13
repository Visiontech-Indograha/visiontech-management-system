"""
app/modules/auth/repositories/auth_session_repository.py

Repository akses data persistensi untuk sesi pengguna (vms.auth_session, login attempt, token family).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.4.
"""
from app.crud.crud_session import CRUDSession


class AuthSessionRepository(CRUDSession):
    """
    Repository akses data sesi perangkat pengguna dan pencatatan audit login.
    """

