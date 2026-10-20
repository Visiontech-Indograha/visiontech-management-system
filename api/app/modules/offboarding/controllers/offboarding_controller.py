"""
app/modules/offboarding/controllers/offboarding_controller.py
Controller orkestrasi use case offboarding karyawan dan clearance aset.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.offboarding.dependencies import get_offboarding_service
from app.modules.offboarding.schemas.offboarding_schema import (
    ClearanceItemVerify,
    OffboardingApprove,
    OffboardingCreate,
    OffboardingDetail,
    OffboardingListItem,
)
from app.modules.offboarding.services.offboarding_service import OffboardingService


class OffboardingController:
    """Controller use case proses pengunduran diri/offboarding dan serah terima aset."""

    def __init__(self, offboarding_service: OffboardingService = Depends(get_offboarding_service)) -> None:
        self.service = offboarding_service

    async def handle_list_offboardings(
        self,
        current_user: CurrentUser,
        status: str | None = None,
    ) -> list[OffboardingListItem]:
        rows = await self.service.list_offboardings(status)
        return [OffboardingListItem(**dict(r._mapping)) for r in rows]

    async def handle_get_offboarding(
        self,
        current_user: CurrentUser,
        offboarding_id: UUID,
    ) -> OffboardingDetail:
        data = await self.service.get_offboarding(offboarding_id)
        return OffboardingDetail(**data)

    async def handle_create_offboarding(
        self,
        current_user: CurrentUser,
        data: OffboardingCreate,
    ) -> OffboardingListItem:
        row = await self.service.create_offboarding(data)
        return OffboardingListItem(**dict(row._mapping))

    async def handle_verify_clearance(
        self,
        current_user: CurrentUser,
        clearance_item_id: UUID,
        data: ClearanceItemVerify,
    ) -> dict[str, str]:
        await self.service.verify_clearance_item(clearance_item_id, UUID(current_user.user_id), data)
        return {"message": "Aset berhasil diverifikasi dan dicatat pengembaliannya."}

    async def handle_approve_offboarding(
        self,
        current_user: CurrentUser,
        offboarding_id: UUID,
        data: OffboardingApprove,
    ) -> OffboardingListItem:
        row = await self.service.approve_offboarding(offboarding_id, UUID(current_user.user_id), data)
        return OffboardingListItem(**dict(row._mapping))
