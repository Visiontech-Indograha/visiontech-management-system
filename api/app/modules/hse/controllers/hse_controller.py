"""
api/app/modules/hse/controllers/hse_controller.py

Controller penanganan request HTTP untuk modul HSE.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import Request

from app.core.rate_limit import client_ip
from app.core.security import CurrentUser
from app.modules.hse.schemas.hse_schema import (
    HseAcknowledgeCreate,
    HseCampaignAuditStats,
    HseCampaignCreate,
    HseCampaignResponse,
    HseCampaignUpdate,
    VehicleInspectionCreate,
    VehicleInspectionResponse,
    VehicleInspectionVerify,
)
from app.modules.hse.services.hse_service import HseService


class HseController:
    def __init__(self, service: HseService) -> None:
        self.service = service

    async def list_campaigns(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
        target_audience: str | None = None,
    ) -> list[HseCampaignResponse]:
        return await self.service.list_campaigns(
            limit=limit,
            offset=offset,
            is_active=is_active,
            target_audience=target_audience,
        )

    async def create_campaign(
        self,
        data: HseCampaignCreate,
        current_user: CurrentUser,
    ) -> HseCampaignResponse:
        return await self.service.create_campaign(data, current_user)

    async def get_campaign(self, campaign_id: UUID) -> HseCampaignResponse:
        return await self.service.get_campaign(campaign_id)

    async def update_campaign(
        self,
        campaign_id: UUID,
        data: HseCampaignUpdate,
        current_user: CurrentUser,
    ) -> HseCampaignResponse:
        return await self.service.update_campaign(campaign_id, data, current_user)

    async def delete_campaign(self, campaign_id: UUID) -> dict[str, bool]:
        success = await self.service.delete_campaign(campaign_id)
        return {"success": success}

    async def get_active_popup(self, current_user: CurrentUser) -> dict[str, Any]:
        campaign = await self.service.get_active_popup(current_user)
        return {"campaign": campaign}
    async def acknowledge_campaign(
        self,
        campaign_id: UUID,
        current_user: CurrentUser,
        data: HseAcknowledgeCreate,
        request: Request,
    ) -> dict[str, Any]:
        result = await self.service.acknowledge_campaign(
            campaign_id=campaign_id,
            current_user=current_user,
            data=data,
            ip_address=client_ip(request),
        )
        return {"acknowledged": True, "detail": result}

    async def get_campaign_audit_stats(
        self, campaign_id: UUID, user: CurrentUser | None = None,
    ) -> HseCampaignAuditStats:
        return await self.service.get_campaign_audit_stats(campaign_id, user)

    async def list_vehicle_inspections(
        self,
        vehicle_id: UUID | None = None,
        period_type: str | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
        user: CurrentUser | None = None,
    ) -> list[VehicleInspectionResponse]:
        return await self.service.list_vehicle_inspections(
            vehicle_id=vehicle_id,
            period_type=period_type,
            status=status,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
            user=user,
        )

    async def create_vehicle_inspection(
        self,
        data: VehicleInspectionCreate,
        current_user: CurrentUser,
    ) -> VehicleInspectionResponse:
        return await self.service.create_vehicle_inspection(data, current_user)

    async def get_vehicle_inspection(
        self, inspection_id: UUID, user: CurrentUser | None = None,
    ) -> VehicleInspectionResponse:
        return await self.service.get_vehicle_inspection(inspection_id, user)

    async def verify_vehicle_inspection(
        self,
        inspection_id: UUID,
        data: VehicleInspectionVerify,
        current_user: CurrentUser,
    ) -> VehicleInspectionResponse:
        return await self.service.verify_vehicle_inspection(inspection_id, data, current_user)

