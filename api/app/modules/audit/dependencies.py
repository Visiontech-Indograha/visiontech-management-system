"""
app/modules/audit/dependencies.py

Perakitan service modul audit untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.audit.repositories.audit_repository import CRUDAudit
from app.modules.audit.services.audit_service import AuditService


def get_audit_service(db: AsyncSession = Depends(get_db_with_user)) -> AuditService:
    return AuditService(CRUDAudit(db))
