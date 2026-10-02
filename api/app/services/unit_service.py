"""
app/services/unit_service.py
Unit bisnis milik organisasi pengguna — bukan data rahasia, terbuka untuk semua peran di organisasinya.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.crud.crud_unit import CRUDUnit


class UnitService:
    def __init__(self, repo: CRUDUnit) -> None:
        self.repo = repo

    async def list_units(self, org_id: UUID | str) -> list[Any]:
        return await self.repo.list_for_org(org_id)
