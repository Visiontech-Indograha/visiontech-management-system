"""Perakitan service dokumen kendaraan (satu permintaan = satu transaksi)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.modules.vehicle_documents.repositories.vehicle_document_repository import VehicleDocumentRepository
from app.modules.vehicle_documents.services.vehicle_document_service import VehicleDocumentService


def get_vehicle_document_service(db: AsyncSession = Depends(get_db_with_user)) -> VehicleDocumentService:
    return VehicleDocumentService(VehicleDocumentRepository(db))
