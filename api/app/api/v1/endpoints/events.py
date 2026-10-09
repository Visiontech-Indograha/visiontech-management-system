"""
Aliran peristiwa waktu nyata (SSE) untuk web dan HP (Rencana Kerja v3, T8).

Sengaja TIDAK memakai dependensi yang membuka sesi basis data: sambungan hidup lama dan tidak boleh menahan
transaksi. Token JWT hanya divalidasi sekali saat menyambung; aliran ditutup saat token kedaluwarsa dan klien
menyambung lagi dengan token baru. Broker di memori satu proses: lihat `app/core/events.py`.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import _unauthenticated, security
from app.core.events import broker
from app.core.security import verify_jwt_token
from app.core.time import utcnow

router = APIRouter(tags=["Events"])
PING_SECONDS = 25


@router.get("/events")
async def events(request: Request,
                 credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> StreamingResponse:
    """
    Aliran `text/event-stream` peristiwa untuk pengguna yang sedang masuk (GET).

    Format: `event: <topic>` + `data: <json>`; topik `notification`, `plan`, `attendance`. Komentar `: ping` tiap
    25 detik menjaga sambungan tetap hidup di balik proksi.
    """
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

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
