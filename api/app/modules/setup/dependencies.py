"""Perakitan service penyiapan awal untuk FastAPI `Depends` (satu permintaan = satu transaksi)."""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rate_limit import client_ip
from app.modules.setup.repositories.setup_repository import SetupRepository
from app.modules.setup.services.setup_service import SetupService


def get_setup_service(request: Request, db: AsyncSession = Depends(get_db)) -> SetupService:
    return SetupService(SetupRepository(db), client_ip(request))
