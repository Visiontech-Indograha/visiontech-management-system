"""
app/modules/exports/controllers/export_controller.py

Controller ekspor dokumen: hasil builder dikembalikan sebagai berkas unduhan + metadata registrinya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.responses import Response

from app.core.security import CurrentUser
from app.modules.exports.dependencies import get_export_service
from app.modules.exports.schemas.export_schema import CompletionExportRequest, ExportOut, PeriodicExportRequest
from app.modules.exports.services.export_service import MIME, ExportService, file_name


def _out(record: Any) -> ExportOut:
    return ExportOut(**dict(record._mapping), file_name=file_name(record))


def _file(record: Any, content: bytes) -> Response:
    return Response(
        content=content,
        media_type=MIME.get(record.export_format, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{file_name(record)}"',
                 "X-Export-Id": str(record.export_id)},
    )


class ExportController:
    def __init__(self, service: ExportService = Depends(get_export_service)) -> None:
        self.service = service

    async def export_completion(self, user: CurrentUser, completion_id: UUID,
                                body: CompletionExportRequest) -> Response:
        return _file(*await self.service.export_completion(user, completion_id, body.template))

    async def list_for_completion(self, user: CurrentUser, completion_id: UUID) -> list[ExportOut]:
        return [_out(r) for r in await self.service.list_for_completion(user, completion_id)]

    async def export_periodic(self, user: CurrentUser, body: PeriodicExportRequest) -> Response:
        return _file(*await self.service.export_periodic(user, body.division_id, body.start_date, body.end_date,
                                                        body.export_format))

    async def list_periodic(self, user: CurrentUser) -> list[ExportOut]:
        return [_out(r) for r in await self.service.list_periodic(user)]

    async def download(self, user: CurrentUser, export_id: UUID) -> Response:
        return _file(*await self.service.download(user, export_id))
