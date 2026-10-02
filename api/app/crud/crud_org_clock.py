"""
app/crud/crud_org_clock.py
Jam organisasi (V-10): waktu & tanggal lokal menurut `organization.timezone`, dari jam server
basis data — sama dengan yang dipakai trigger dan kueri lain (`now() AT TIME ZONE o.timezone`).
Bukan jam perangkat, bukan zona waktu mesin aplikasi (Docker = UTC).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDOrgClock(CRUDBase):

    async def local_now(self, org_id: UUID | str) -> Any:
        """Baris `(local_now, today)` untuk organisasi."""
        return await self.fetchone(
            """
            SELECT (now() AT TIME ZONE o.timezone) AS local_now,
                   (now() AT TIME ZONE o.timezone)::date AS today
            FROM vms.organization o WHERE o.id = CAST(:org AS uuid)
            """,
            {"org": org_id},
        )

    async def day_reached(self, day_id: UUID | str) -> Any:
        """Apakah tanggal hari kerja sudah tiba menurut zona waktu organisasi SK-nya. None = hari tidak ada."""
        return await self.scalar(
            """
            SELECT d.work_date <= (now() AT TIME ZONE o.timezone)::date
            FROM vms.work_plan_day d
            JOIN vms.work_plan w ON w.id = d.work_plan_id
            JOIN vms.organization o ON o.id = w.organization_id
            WHERE d.id = :day
            """,
            {"day": day_id},
        )
