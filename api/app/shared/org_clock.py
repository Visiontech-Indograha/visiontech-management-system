"""
app/shared/org_clock.py
Waktu server lokal berbasis zona waktu Asia/Jakarta (WIB) Master Schema V2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


class CRUDOrgClock(CRUDBase):
    """
    Kelas CRUD untuk operasi waktu dan tanggal lokal.
    """

    async def local_now(self, org_id: UUID | str | None = None) -> Any:
        """Baris `(local_now, today)` untuk organisasi."""
        return await self.fetchone(
            """
            SELECT (now() AT TIME ZONE 'Asia/Jakarta') AS local_now,
                   (now() AT TIME ZONE 'Asia/Jakarta')::date AS today
            """
        )

    async def day_reached(self, day_id: UUID | str) -> Any:
        """Apakah tanggal hari kerja sudah tiba menurut zona waktu lokal."""
        return await self.scalar(
            """
            SELECT d.work_date <= (now() AT TIME ZONE 'Asia/Jakarta')::date
            FROM work_plan_daily d
            WHERE d.daily_plan_id = CAST(:day AS uuid)
            """,
            {"day": str(day_id)},
        )
