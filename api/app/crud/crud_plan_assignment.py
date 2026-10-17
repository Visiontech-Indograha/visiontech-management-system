"""Data pembuat SK dan cakupan divisi personel Master Schema V2 (tabel employee, users, division)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanAssignment(CRUDBase):
    """
    Kelas CRUD untuk mengelola data pembuat SK dan penugasan/pencarian personel per divisi (Master Schema V2).
    """

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """Mengambil data ID pegawai dan ID divisi dari pengguna."""
        return await self.fetchone(
            """
            SELECT e.employee_id::text AS employee_id, e.division_id::text AS unit_id
            FROM users u
            JOIN employee e ON e.employee_id = u.employee_id
            WHERE u.user_id = CAST(:user AS uuid) AND u.is_active AND u.delete_at IS NULL
              AND e.offboarding_status = 'active' AND e.delete_at IS NULL
            """,
            {"user": str(user_id)},
        )

    async def employee_units(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> dict[str, str | None]:
        """Mengambil pemetaan ID divisi untuk sejumlah pegawai."""
        ids = [str(value) for value in employee_ids]
        if not ids:
            return {}
        rows = await self.fetchall(
            """
            SELECT employee_id::text AS employee_id, division_id::text AS unit_id
            FROM employee
            WHERE employee_id = ANY(CAST(:ids AS uuid[]))
              AND offboarding_status = 'active' AND delete_at IS NULL
            """,
            {"ids": ids},
        )
        return {str(row.employee_id): str(row.unit_id) if row.unit_id else None for row in rows}

    async def active_project_managers(self, org_id: UUID | str) -> list[Any]:
        """Mengambil daftar Project Manager (PM) yang aktif."""
        return list(
            await self.fetchall(
                """
            SELECT DISTINCT e.employee_id AS id, e.full_name, 'Project Manager' AS position, e.division_id AS unit_id
            FROM employee e
            JOIN users u ON u.employee_id = e.employee_id AND u.is_active AND u.delete_at IS NULL
            WHERE u.system_role = 'PROJECT_MANAGER'
              AND e.offboarding_status = 'active' AND e.delete_at IS NULL
            ORDER BY e.full_name
            """
            )
        )

    async def available_personnel(
        self,
        org_id: UUID | str,
        period_start: date,
        period_end: date,
        unit_id: UUID | str | None,
        include_pm: bool = False,
    ) -> list[Any]:
        """Mengambil data pegawai lapangan yang tersedia untuk ditugaskan."""
        roles = "('PROJECT_MANAGER', 'TEAM_LEADER', 'EMPLOYEE')" if include_pm else "('TEAM_LEADER', 'EMPLOYEE')"
        return list(
            await self.fetchall(
                f"""
            SELECT e.employee_id AS id, e.full_name,
                   CASE WHEN u.system_role = 'TEAM_LEADER' THEN 'Team Leader'
                        WHEN u.system_role = 'PROJECT_MANAGER' THEN 'Project Manager'
                        ELSE 'Teknisi Lapangan' END AS position,
                   e.division_id AS unit_id
            FROM employee e
            JOIN users u ON u.employee_id = e.employee_id AND u.is_active AND u.delete_at IS NULL
            WHERE e.offboarding_status = 'active' AND e.delete_at IS NULL
              AND u.system_role IN {roles}
              AND (CAST(:unit AS uuid) IS NULL OR e.division_id = CAST(:unit AS uuid))
            ORDER BY e.full_name
            """,
                {"unit": str(unit_id) if unit_id else None},
            )
        )

    async def eligible_field_staff(
        self,
        employee_ids: Iterable[UUID | str],
        org_id: UUID | str,
    ) -> set[str]:
        """Menyaring kumpulan ID pegawai berstatus teknisi / ketua tim."""
        ids = [str(value) for value in employee_ids]
        if not ids:
            return set()
        rows = await self.fetchall(
            """
            SELECT e.employee_id::text AS employee_id
            FROM employee e
            JOIN users u ON u.employee_id = e.employee_id AND u.is_active AND u.delete_at IS NULL
            WHERE e.employee_id = ANY(CAST(:ids AS uuid[]))
              AND e.offboarding_status = 'active' AND e.delete_at IS NULL
              AND u.system_role IN ('TEAM_LEADER', 'EMPLOYEE')
            """,
            {"ids": ids},
        )
        return {str(row.employee_id) for row in rows}
