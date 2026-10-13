"""
app/crud/crud_emergency_contact.py

Kueri kontak darurat karyawan (daftar, detail, tambah, ubah, hapus).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDEmergencyContact(CRUDBase):
    """
    Operasi CRUD basis data untuk kontak darurat karyawan.
    """

    _COLUMNS = """id, organization_id, employee_id, name, relationship, phone, address,
                  is_primary, created_at, updated_at"""

    async def list_by_employee(self, employee_id: UUID | str, org_id: UUID | str) -> list[Any]:
        """
        Mendapatkan semua kontak darurat karyawan pada organisasi tertentu,
        diurutkan dari kontak utama, kemudian waktu dibuat.
        """
        return list(
            await self.fetchall(
                f"""
                SELECT {self._COLUMNS}
                FROM vms.employee_emergency_contact
                WHERE employee_id = :emp_id AND organization_id = :org_id
                ORDER BY is_primary DESC, created_at ASC
                """,
                {"emp_id": employee_id, "org_id": org_id},
            )
        )

    async def get(self, contact_id: UUID | str, employee_id: UUID | str, org_id: UUID | str) -> Any | None:
        """
        Mendapatkan satu baris kontak darurat berdasarkan ID, employee_id, dan organization_id.
        """
        return await self.fetchone(
            f"""
            SELECT {self._COLUMNS}
            FROM vms.employee_emergency_contact
            WHERE id = :id AND employee_id = :emp_id AND organization_id = :org_id
            """,
            {"id": contact_id, "emp_id": employee_id, "org_id": org_id},
        )

    async def reset_primary(
        self, employee_id: UUID | str, org_id: UUID | str, except_id: UUID | str | None = None
    ) -> None:
        """
        Mengubah status is_primary menjadi false untuk semua kontak darurat karyawan ini,
        kecuali ID yang dikecualikan (jika ada).
        """
        query = """
            UPDATE vms.employee_emergency_contact
            SET is_primary = false, updated_at = now()
            WHERE employee_id = :emp_id AND organization_id = :org_id
        """
        params: dict[str, Any] = {"emp_id": employee_id, "org_id": org_id}
        if except_id:
            query += " AND id != :except_id"
            params["except_id"] = except_id
        await self.execute(query, params)

    async def insert(self, org_id: UUID | str, employee_id: UUID | str, data: dict[str, Any]) -> Any:
        """
        Menambahkan kontak darurat baru untuk karyawan.
        """
        is_primary = data.get("is_primary", True)
        if is_primary:
            await self.reset_primary(employee_id, org_id)

        return await self.fetchone(
            f"""
            INSERT INTO vms.employee_emergency_contact (
                organization_id, employee_id, name, relationship, phone, address, is_primary
            )
            VALUES (:org_id, :emp_id, :name, :relationship, :phone, :address, :is_primary)
            RETURNING {self._COLUMNS}
            """,
            {
                "org_id": org_id,
                "emp_id": employee_id,
                "name": data["name"],
                "relationship": data["relationship"],
                "phone": data["phone"],
                "address": data.get("address"),
                "is_primary": is_primary,
            },
        )

    async def update_fields(
        self, contact_id: UUID | str, employee_id: UUID | str, org_id: UUID | str, fields: dict[str, Any]
    ) -> Any | None:
        """
        Memperbarui kolom kontak darurat tertentu.
        """
        if fields.get("is_primary"):
            await self.reset_primary(employee_id, org_id, except_id=contact_id)

        assignments = ", ".join(f"{name} = :{name}" for name in fields)
        return await self.fetchone(
            f"""
            UPDATE vms.employee_emergency_contact
            SET {assignments}, updated_at = now()
            WHERE id = :id AND employee_id = :emp_id AND organization_id = :org_id
            RETURNING {self._COLUMNS}
            """,
            {"id": contact_id, "emp_id": employee_id, "org_id": org_id, **fields},
        )

    async def delete(self, contact_id: UUID | str, employee_id: UUID | str, org_id: UUID | str) -> bool:
        """
        Menghapus kontak darurat.
        """
        deleted = await self.scalar(
            """
            DELETE FROM vms.employee_emergency_contact
            WHERE id = :id AND employee_id = :emp_id AND organization_id = :org_id
            RETURNING id
            """,
            {"id": contact_id, "emp_id": employee_id, "org_id": org_id},
        )
        return deleted is not None
