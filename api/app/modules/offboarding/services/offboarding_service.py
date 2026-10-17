"""
app/modules/offboarding/services/offboarding_service.py
Service logika bisnis untuk offboarding karyawan dan clearance pengembalian aset.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_with_user
from app.core.errors import NotFoundError, ValidationError
from app.modules.offboarding.repositories.offboarding_repository import OffboardingRepository
from app.modules.offboarding.schemas.offboarding_schema import (
    ClearanceItemVerify,
    OffboardingApprove,
    OffboardingCreate,
)


class OffboardingService:
    """Service use case offboarding dan clearance aset."""

    def __init__(self, db: AsyncSession = Depends(get_db_with_user)) -> None:
        self.repo = OffboardingRepository(db)

    async def list_offboardings(self, status: str | None = None) -> Sequence[Any]:
        return await self.repo.list_offboardings(status)

    async def get_offboarding(self, offboarding_id: UUID) -> Any:
        record = await self.repo.get_offboarding_by_id(offboarding_id)
        if not record:
            raise NotFoundError("Data pengajuan offboarding tidak ditemukan.")
        items = await self.repo.list_clearance_items(offboarding_id)
        data = dict(record._mapping)
        data["clearance_items"] = [dict(i._mapping) for i in items]
        return data

    async def create_offboarding(self, data: OffboardingCreate) -> Any:
        return await self.repo.create_offboarding(data)

    async def verify_clearance_item(
        self, clearance_item_id: UUID, verifier_id: UUID, data: ClearanceItemVerify
    ) -> Any:
        res = await self.repo.verify_clearance_item(clearance_item_id, verifier_id, data)
        if not res:
            raise NotFoundError("Item clearance aset tidak ditemukan.")
        return res

    async def approve_offboarding(
        self, offboarding_id: UUID, approver_id: UUID, data: OffboardingApprove
    ) -> Any:
        record = await self.repo.get_offboarding_by_id(offboarding_id)
        if not record:
            raise NotFoundError("Data pengajuan offboarding tidak ditemukan.")
        if data.approval_type.upper() == "HR" and not record.is_all_assets_returned:
            raise ValidationError("Persetujuan akhir HR memerlukan seluruh aset dikembalikan (Clearance Lengkap).")
        return await self.repo.approve_offboarding(offboarding_id, data.approval_type, approver_id)
