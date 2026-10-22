"""
app/modules/work_plans/controllers/survey_controller.py
Controller survei ACS & CCTV berformat baku (docs/37).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.work_plans.dependencies import get_survey_service
from app.modules.work_plans.schemas.survey_schema import (
    CatalogAddIn,
    LineEditIn,
    PlanFromSurveyIn,
    PlanFromSurveyOut,
    PointIn,
    PointLine,
    PointLocationIn,
    ReportIn,
    ReviewIn,
    SurveyListItem,
    SurveyOut,
)
from app.modules.work_plans.services.survey_service import SurveyService


class SurveyController:
    """Controller survei per titik."""

    def __init__(self, service: SurveyService = Depends(get_survey_service)) -> None:
        self.service = service

    async def list_surveys(self, user: CurrentUser, state: str | None) -> list[SurveyListItem]:
        return [SurveyListItem(**r) for r in await self.service.list_surveys(user, state)]

    async def detail(self, user: CurrentUser, task_id: UUID) -> SurveyOut:
        return SurveyOut(**await self.service.detail(user, task_id))

    async def add_point(self, user: CurrentUser, task_id: UUID, data: PointIn) -> SurveyOut:
        return SurveyOut(**await self.service.add_point(user, task_id, data))

    async def update_point(self, user: CurrentUser, point_id: UUID, data: PointIn) -> SurveyOut:
        return SurveyOut(**await self.service.update_point(user, point_id, data))

    async def move_point(self, user: CurrentUser, point_id: UUID, data: PointLocationIn) -> SurveyOut:
        return SurveyOut(**await self.service.move_point(user, point_id, data))

    async def delete_point(self, user: CurrentUser, point_id: UUID) -> SurveyOut:
        return SurveyOut(**await self.service.delete_point(user, point_id))

    async def add_general_line(self, user: CurrentUser, task_id: UUID, data: PointLine) -> SurveyOut:
        return SurveyOut(**await self.service.add_general_line(user, task_id, data))

    async def edit_line(self, user: CurrentUser, bom_id: UUID, data: LineEditIn) -> SurveyOut:
        return SurveyOut(**await self.service.edit_line(user, bom_id, data))

    async def delete_line(self, user: CurrentUser, bom_id: UUID) -> SurveyOut:
        return SurveyOut(**await self.service.delete_line(user, bom_id))

    async def add_to_catalog(self, user: CurrentUser, task_id: UUID, data: CatalogAddIn) -> SurveyOut:
        return SurveyOut(**await self.service.add_to_catalog(user, task_id, data))

    async def save_report(self, user: CurrentUser, task_id: UUID, data: ReportIn) -> SurveyOut:
        return SurveyOut(**await self.service.save_report(user, task_id, data))

    async def submit(self, user: CurrentUser, task_id: UUID) -> SurveyOut:
        return SurveyOut(**await self.service.submit(user, task_id))

    async def review(self, user: CurrentUser, task_id: UUID, data: ReviewIn) -> SurveyOut:
        return SurveyOut(**await self.service.review(user, task_id, data))

    async def plan(self, user: CurrentUser, task_id: UUID, data: PlanFromSurveyIn) -> PlanFromSurveyOut:
        daily_id, created = await self.service.plan_from_survey(user, task_id, data)
        return PlanFromSurveyOut(daily_plan_id=daily_id, created_item_ids=created)
