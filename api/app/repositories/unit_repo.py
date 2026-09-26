"""
app/repositories/unit_repo.py
Unit bisnis organisasi (pilihan unit untuk mutasi/promosi, R-19).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class UnitRepo(BaseRepo):

    async def list_for_org(self, org_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            "SELECT id, code, name FROM vms.business_unit WHERE organization_id = :org ORDER BY name",
            {"org": org_id}))
