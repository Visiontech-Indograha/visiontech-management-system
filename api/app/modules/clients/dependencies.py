"""Perakitan service modul clients (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.clients.repositories.client_repository import ClientRepository
from app.modules.clients.services.client_service import ClientService


def get_client_service(db: AsyncSession = Depends(get_db_with_user)) -> ClientService:
    return ClientService(ClientRepository(db))
