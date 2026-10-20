"""
app/modules/signatures/dependencies.py

Perakitan service modul signatures untuk FastAPI `Depends` (dipindah dari api/deps.py).
Getter memakai dependency sesi yang SAMA dengan handler sehingga satu permintaan = satu transaksi.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_db_with_user
from app.modules.signatures.services.signature_service import SignatureService


def get_signature_service(db: AsyncSession = Depends(get_db_with_user)) -> SignatureService:
    return SignatureService(db)


def get_public_signature_service(db: AsyncSession = Depends(get_db)) -> SignatureService:
    return SignatureService(db)
