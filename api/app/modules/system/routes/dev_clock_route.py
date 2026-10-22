"""
app/modules/system/routes/dev_clock_route.py
Jam simulasi untuk uji skenario lapangan multi-minggu di lingkungan pengembangan (bukan produksi).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_permission
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import set_dev_today

router = APIRouter(prefix="/system", tags=["System"])


class DevClockIn(BaseModel):
    day: date | None = None  # None = kembali ke tanggal nyata


class DevClockOut(BaseModel):
    today: date


@router.put("/dev-clock", response_model=DevClockOut, include_in_schema=False)
def set_dev_clock(data: DevClockIn,
                  _: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN))) -> DevClockOut:
    """Geser tanggal bisnis server (hanya APP_ENV bukan production)."""
    if settings.APP_ENV.strip().lower() == "production":
        raise NotFoundError("Halaman")
    return DevClockOut(today=set_dev_today(data.day))
