"""
app/modules/offboarding/controllers/offboarding_controller.py
Controller offboarding PKWT & clearance aset (Milestone 9).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.offboarding.dependencies import get_offboarding_service
from app.modules.offboarding.schemas.offboarding_schema import (
    ClearanceItemVerify,
    CompleteDueResult,
    OffboardingCreate,
    OffboardingDetail,
    OffboardingListItem,
    PkwtExpiringRow,
)
from app.modules.offboarding.services.offboarding_service import OffboardingService


class OffboardingController:
    def __init__(self, service: OffboardingService = Depends(get_offboarding_service)) -> None:
        self.service = service

    async def list_all(self, user: CurrentUser, status: str | None) -> list[OffboardingListItem]:
        return [OffboardingListItem(**dict(r._mapping)) for r in await self.service.list_all(user, status)]

    async def detail(self, user: CurrentUser, offboarding_id: UUID) -> OffboardingDetail:
        return OffboardingDetail(**await self.service.detail(user, offboarding_id))

    async def create(self, data: OffboardingCreate, user: CurrentUser | None = None) -> OffboardingDetail:
        return OffboardingDetail(**await self.service.create(data, user))

    async def verify_item(self, user: CurrentUser, item_id: UUID, data: ClearanceItemVerify) -> OffboardingDetail:
        return OffboardingDetail(**await self.service.verify_item(user, item_id, data))

    async def approve(self, user: CurrentUser, offboarding_id: UUID, approval_type: str) -> OffboardingDetail:
        return OffboardingDetail(**await self.service.approve(user, offboarding_id, approval_type))

    async def cancel(self, user: CurrentUser, offboarding_id: UUID, reason: str) -> dict[str, str]:
        await self.service.cancel(user, offboarding_id, reason)
        return {"message": "Offboarding dibatalkan; karyawan aktif kembali."}

    async def pkwt_expiring(self, user: CurrentUser, days: int) -> list[PkwtExpiringRow]:
        return [PkwtExpiringRow(**dict(r._mapping)) for r in await self.service.pkwt_expiring(user, days)]

    async def complete_due(self) -> CompleteDueResult:
        return CompleteDueResult(completed=await self.service.complete_due())
