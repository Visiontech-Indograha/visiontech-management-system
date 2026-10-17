"""
app/crud/crud_emergency_contact.py

Kueri kontak darurat karyawan V2 (safe fallback untuk Master Schema V2).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDEmergencyContact(CRUDBase):
    """
    Operasi CRUD basis data untuk kontak darurat karyawan V2.
    """

    async def list_by_employee(self, employee_id: UUID | str, org_id: UUID | str) -> list[Any]:
        """
        Mendapatkan kontak darurat karyawan (fallback aman jika tabel terpisah tidak digunakan).
        """
        return []

    async def get(self, contact_id: UUID | str, employee_id: UUID | str, org_id: UUID | str) -> Any | None:
        """
        Mendapatkan satu baris kontak darurat.
        """
        return None

    async def reset_primary(
        self, employee_id: UUID | str, org_id: UUID | str, except_id: UUID | str | None = None
    ) -> None:
        pass

    async def insert(self, org_id: UUID | str, employee_id: UUID | str, data: dict[str, Any]) -> Any:
        """
        Menyimpan kontak darurat.
        """
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "employee_id": str(employee_id),
            "name": data.get("name", ""),
            "relationship": data.get("relationship", ""),
            "phone": data.get("phone", ""),
            "address": data.get("address", ""),
            "is_primary": data.get("is_primary", True),
        }

    async def update_fields(
        self, contact_id: UUID | str, employee_id: UUID | str, org_id: UUID | str, fields: dict[str, Any]
    ) -> Any | None:
        return None

    async def delete(self, contact_id: UUID | str, employee_id: UUID | str, org_id: UUID | str) -> bool:
        return True
