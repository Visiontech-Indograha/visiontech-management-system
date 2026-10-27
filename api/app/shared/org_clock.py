"""
app/shared/org_clock.py
Waktu server lokal berbasis zona waktu Asia/Jakarta (WIB) Master Schema V2.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase
from app.core.time import jakarta_now


class OrgClockResult:
    """Objek hasil waktu lokal organisasi yang kompatibel dengan atribut dan indeks mapping."""

    def __init__(self, local_now: datetime, today: date) -> None:
        self.local_now = local_now
        self.today = today

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    @property
    def _mapping(self) -> dict[str, Any]:
        return {"local_now": self.local_now, "today": self.today}


class CRUDOrgClock(CRUDBase):
    """
    Kelas CRUD untuk operasi waktu dan tanggal lokal.
    Mendukung sinkronisasi dev-clock simulasi di environment pengembangan.
    """

    async def local_now(self, org_id: UUID | str | None = None) -> Any:
        """Baris `(local_now, today)` untuk organisasi."""
        j_now = jakarta_now()
        return OrgClockResult(local_now=j_now, today=j_now.date())

    async def day_reached(self, day_id: UUID | str) -> Any:
        """Apakah tanggal hari kerja sudah tiba menurut zona waktu lokal."""
        j_today = jakarta_now().date()
        return await self.scalar(
            """
            SELECT d.work_date <= :today
            FROM work_plan_daily d
            WHERE d.daily_plan_id = CAST(:day AS uuid)
            """,
            {"day": str(day_id), "today": j_today},
        )
