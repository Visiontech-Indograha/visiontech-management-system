"""
app/modules/auth/dependencies.py

Perakitan service modul auth untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB_SCOPE, get_db
from app.modules.auth.services.auth_flow_service import AuthFlowService


def get_auth_flow_service(db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> AuthFlowService:
    return AuthFlowService(db)
