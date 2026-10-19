"""
app/services/unit_service.py
Unit bisnis milik organisasi pengguna — bukan data rahasia, terbuka untuk semua peran di organisasinya.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.units.repositories.unit_repository import CRUDUnit


class UnitService:
    """
    Layanan untuk mengelola unit bisnis dalam organisasi.
    """

    def __init__(self, repo: CRUDUnit) -> None:
        """
        Inisialisasi UnitService.

        Args:
            repo (CRUDUnit): Repositori untuk operasi CRUD pada entitas unit.
        """
        self.repo = repo

    async def list_units(self, org_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar semua unit untuk sebuah organisasi.
        Karena data unit bukan rahasia, dapat diakses oleh semua peran di organisasi.

        Args:
            org_id (UUID | str): ID organisasi.

        Returns:
            list[Any]: Daftar unit dalam organisasi tersebut.
        """
        return await self.repo.list_for_org(org_id)
