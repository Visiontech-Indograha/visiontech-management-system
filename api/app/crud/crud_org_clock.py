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
    """
    Kelas CRUD untuk operasi yang berkaitan dengan waktu dan zona waktu organisasi.
    """

    async def local_now(self, org_id: UUID | str) -> Any:
        """Baris `(local_now, today)` untuk organisasi.

        Args:
            org_id (UUID | str): ID organisasi.

        Returns:
            Any: Baris data yang menyimpan nilai waktu (timestamp) dan tanggal (date) lokal organisasi.
        """
        # Mengekstrak waktu server (now()) dan mentransformasikannya secara real-time
        # ke zona waktu spesifik organisasi (o.timezone) melalui fitur AT TIME ZONE PostgreSQL.
        return await self.fetchone(
            """
            SELECT (now() AT TIME ZONE o.timezone) AS local_now,
                   (now() AT TIME ZONE o.timezone)::date AS today
            FROM vms.organization o WHERE o.id = CAST(:org AS uuid)
            """,
            {"org": org_id},
        )

    async def day_reached(self, day_id: UUID | str) -> Any:
        """Apakah tanggal hari kerja sudah tiba menurut zona waktu organisasi SK-nya. None = hari tidak ada.

        Args:
            day_id (UUID | str): ID dari entri hari kerja (work_plan_day).

        Returns:
            Any: Boolean evaluasi waktu, atau None.
        """
        # Melakukan JOIN bertingkat dari tabel hari (work_plan_day) ke work_plan lalu ke organization.
        # Membandingkan kolom work_date dengan tanggal lokal terkini dari zona waktu organisasi tersebut
        # untuk menentukan apakah suatu hari kerja SK sudah tiba atau belum.
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

