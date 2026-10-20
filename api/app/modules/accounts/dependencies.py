"""
app/modules/accounts/dependencies.py

Perakitan service modul accounts untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.accounts.services.account_service import AccountService
from app.modules.auth.repositories.auth_session_repository import CRUDSession
from app.modules.auth.repositories.auth_user_repository import CRUDUser
from app.modules.employees.repositories.employee_repository import CRUDEmployee


def get_account_service(db: AsyncSession = Depends(get_db_with_user)) -> AccountService:
    return AccountService(CRUDUser(db), CRUDEmployee(db), CRUDSession(db))
