"""
app/modules/home/controllers/home_controller.py

Controller ringkasan Beranda.
"""

from __future__ import annotations

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.home.dependencies import get_home_service
from app.modules.home.schemas.home_schema import HomeSummary
from app.modules.home.services.home_service import HomeService


class HomeController:
    def __init__(self, service: HomeService = Depends(get_home_service)) -> None:
        self.service = service

    async def handle_summary(self, current_user: CurrentUser) -> HomeSummary:
        return await self.service.summary(current_user)
