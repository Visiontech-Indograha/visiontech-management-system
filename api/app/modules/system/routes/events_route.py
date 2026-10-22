"""
app/modules/system/routes/events_route.py

Rute endpoint HTTP untuk aliran SSE peristiwa waktu nyata (/events).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import security
from app.modules.system.controllers.events_controller import EventsController

router = APIRouter(tags=["Events"])


@router.get("/events")
async def events(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    controller: EventsController = Depends(),
) -> StreamingResponse:
    """
    Aliran `text/event-stream` peristiwa untuk pengguna yang sedang masuk (GET).

    Format: `event: <topic>` + `data: <json>`; topik `notification`, `plan`, `attendance`. Komentar `: ping` tiap
    25 detik menjaga sambungan tetap hidup di balik proksi.
    """
    return await controller.handle_stream(request, credentials)


__all__ = ["router"]
