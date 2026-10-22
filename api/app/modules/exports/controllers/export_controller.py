"""
app/modules/exports/controllers/export_controller.py

Controller ekspor dokumen: hasil builder dikembalikan sebagai berkas unduhan + metadata registrinya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.responses import Response

from app.core.errors import NotFoundError
from app.core.security import CurrentUser
from app.modules.exports.dependencies import get_export_service
from app.modules.exports.schemas.export_schema import (
    CompletionExportRequest,
    ExportOut,
    PeriodicExportRequest,
    SurveyLogoOut,
    TeamWeekExportRequest,
)
from app.modules.exports.services.export_service import MIME, ExportService, file_name
from app.shared.content_disposition import content_disposition


def _out(record: Any) -> ExportOut:
    return ExportOut(**dict(record._mapping), file_name=file_name(record))


def _file(record: Any, content: bytes) -> Response:
    return Response(
        content=content,
        media_type=MIME.get(record.export_format, "application/octet-stream"),
        headers={"Content-Disposition": content_disposition("attachment", file_name(record)),
                 "X-Export-Id": str(record.export_id)},
    )


class ExportController:
    def __init__(self, service: ExportService = Depends(get_export_service)) -> None:
        self.service = service

    async def export_completion(self, user: CurrentUser, completion_id: UUID,
                                body: CompletionExportRequest) -> Response:
        return _file(*await self.service.export_completion(user, completion_id, body.template))

    async def preview_survey(self, user: CurrentUser, task_id: UUID) -> Response:
        export_format, content = await self.service.preview_survey(user, task_id)
        name = f"pratinjau-survei.{'pdf' if export_format == 'PDF' else 'docx'}"
        return Response(content=content, media_type=MIME[export_format],
                        headers={"Content-Disposition": content_disposition("inline", name),
                                 "X-Preview-Format": export_format, "Cache-Control": "no-store"})

    async def export_survey(self, user: CurrentUser, task_id: UUID) -> Response:
        return _file(*await self.service.export_survey(user, task_id))

    def survey_logos(self, user: CurrentUser) -> list[SurveyLogoOut]:
        return [SurveyLogoOut(**x) for x in self.service.survey_logos(user)]

    def survey_logo_image(self, user: CurrentUser, role: str) -> Response:
        data = self.service.survey_logo_image(user, role)
        if data is None:
            raise NotFoundError("Logo")
        return Response(data, media_type="image/png", headers={"Cache-Control": "no-store"})

    def set_survey_logo(self, user: CurrentUser, role: str, raw: bytes) -> list[SurveyLogoOut]:
        return [SurveyLogoOut(**x) for x in self.service.set_survey_logo(user, role, raw)]

    def reset_survey_logo(self, user: CurrentUser, role: str) -> list[SurveyLogoOut]:
        return [SurveyLogoOut(**x) for x in self.service.reset_survey_logo(user, role)]

    async def list_for_completion(self, user: CurrentUser, completion_id: UUID) -> list[ExportOut]:
        return [_out(r) for r in await self.service.list_for_completion(user, completion_id)]

    async def export_periodic(self, user: CurrentUser, body: PeriodicExportRequest) -> Response:
        return _file(*await self.service.export_periodic(user, body.division_id, body.start_date, body.end_date,
                                                        body.export_format))

    async def export_team_week(self, user: CurrentUser, body: TeamWeekExportRequest) -> Response:
        return _file(*await self.service.export_team_week(user, body.team_id, body.start_date))

    async def list_periodic(self, user: CurrentUser) -> list[ExportOut]:
        return [_out(r) for r in await self.service.list_periodic(user)]

    async def download(self, user: CurrentUser, export_id: UUID) -> Response:
        return _file(*await self.service.download(user, export_id))
