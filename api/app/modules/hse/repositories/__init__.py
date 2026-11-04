"""
api/app/modules/hse/repositories/__init__.py
"""
from app.modules.hse.repositories.hse_campaign_repository import HseCampaignRepository
from app.modules.hse.repositories.vehicle_inspection_repository import VehicleInspectionRepository

__all__ = ["HseCampaignRepository", "VehicleInspectionRepository"]

