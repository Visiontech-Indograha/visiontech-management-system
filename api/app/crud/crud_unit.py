"""
app/crud/crud_unit.py
Divisi bisnis organisasi dari tabel division (Master Schema V2).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDUnit(CRUDBase):
    """
    CRUD untuk mengelola data Divisi Bisnis (division).
    """

    async def list_for_org(self, org_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar seluruh divisi yang aktif dalam organisasi.
        """
        return list(
            await self.fetchall(
                """
                SELECT
                    d.division_id AS id,
                    d.division_id,
                    'DIV-' || UPPER(SUBSTRING(d.name FROM 1 FOR 3)) AS code,
                    d.name,
                    d.status,
                    d.om_id,
                    d.pm_id,
                    e_om.full_name AS om_name,
                    e_pm.full_name AS pm_name
                FROM division d
                LEFT JOIN employee e_om ON e_om.employee_id = d.om_id
                LEFT JOIN employee e_pm ON e_pm.employee_id = d.pm_id
                WHERE d.delete_at IS NULL
                ORDER BY d.name
                """,
                {"org": org_id},
            )
        )
