"""
app/crud/crud_unit.py
Unit bisnis organisasi (pilihan unit untuk mutasi/promosi, R-19).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDUnit(CRUDBase):
    """
    CRUD untuk mengelola data Unit Bisnis (Business Unit).
    Menyediakan daftar unit untuk keperluan penempatan atau promosi karyawan (R-19).
    """

    async def list_for_org(self, org_id: UUID | str) -> list[Any]:
        """
        Mengambil daftar seluruh unit bisnis dalam satu organisasi.
        
        Args:
            org_id (UUID | str): ID organisasi.
            
        Returns:
            list[Any]: Daftar record unit bisnis berisi id, kode, dan nama unit.
        """
        # Mengambil daftar unit bisnis dan mengurutkannya secara alfabetis berdasarkan nama.
        return list(await self.fetchall(
            "SELECT id, code, name FROM vms.business_unit WHERE organization_id = :org ORDER BY name",
            {"org": org_id}))
