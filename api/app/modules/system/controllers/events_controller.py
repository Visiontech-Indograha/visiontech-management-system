"""
app/modules/system/controllers/events_controller.py

Controller orkestrasi aliran peristiwa waktu nyata (SSE) untuk web dan HP.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import jwt
from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import _unauthenticated
from app.core.events import broker
from app.core.security import verify_jwt_token
from app.core.time import utcnow

PING_SECONDS = 25


class EventsController:
    """Controller aliran SSE (Server-Sent Events) waktu nyata."""

    async def handle_stream(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> StreamingResponse:
        """Memvalidasi kredensial pengguna dan mengalirkan event SSE ke klien."""
        if credentials is None:
            raise _unauthenticated()
        try:
            payload = verify_jwt_token(credentials.credentials)
        except jwt.PyJWTError:
            raise _unauthenticated() from None
        user_id, expires = payload.get("sub"), float(payload.get("exp") or 0)
        if not user_id or expires <= utcnow().timestamp():
            raise _unauthenticated()

        async def stream() -> AsyncIterator[str]:
            queue = broker.subscribe(str(user_id))
            try:
                yield ": connected\n\n"
                while utcnow().timestamp() < expires:
                    if await request.is_disconnected():
                        break
                    try:
                        wait = max(0.1, min(PING_SECONDS, expires - utcnow().timestamp()))
                        event = await asyncio.wait_for(queue.get(), timeout=wait)
                    except TimeoutError:
                        yield ": ping\n\n"
                        continue
                    yield f"event: {event['topic']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            finally:
                broker.unsubscribe(str(user_id), queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )


__all__ = ["PING_SECONDS", "EventsController"]

