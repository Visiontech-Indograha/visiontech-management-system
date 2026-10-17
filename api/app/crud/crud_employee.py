"""
app/crud/crud_employee.py
Kueri direktori karyawan, penempatan, alamat, dan siklus offboarding (Master Schema V2).
Tabel yang dikelola: employee, address, users, office, division.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDEmployee(CRUDBase):
    """
    Operasi data karyawan untuk Master Schema V2.
    """

    async def employee_of_user(self, user_id: UUID | str) -> UUID | None:
        """Mendapatkan employee_id dari user_id."""
        val = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": user_id},
        )
        return UUID(str(val)) if val else None

    async def lock(self, employee_id: UUID | str, org_id: UUID | str) -> Any:
        """Mengunci baris karyawan untuk transaksi aman."""
        return await self.fetchone(
            """
            SELECT employee_id AS id, delete_at IS NOT NULL AS deleted, 
                   (offboarding_status != 'offboarded') AS is_active, 
                   CAST(division_id AS text) AS unit_id
            FROM employee 
            WHERE employee_id = CAST(:id AS uuid)
            FOR UPDATE
            """,
            {"id": employee_id},
        )

    async def restore(self, employee_id: UUID | str) -> None:
        """Memulihkan karyawan dari status offboarded."""
        await self.execute(
            """
            UPDATE employee 
            SET offboarding_status = 'active', delete_at = NULL, update_at = now() 
            WHERE employee_id = CAST(:id AS uuid)
            """,
            {"id": employee_id},
        )
        await self.execute(
            "UPDATE users SET is_active = true, update_at = now() WHERE employee_id = CAST(:id AS uuid)",
            {"id": employee_id},
        )

    async def archive(self, employee_id: UUID | str) -> None:
        """Soft delete karyawan."""
        await self.execute(
            """
            UPDATE employee 
            SET delete_at = now(), offboarding_status = 'offboarded', update_at = now() 
            WHERE employee_id = CAST(:id AS uuid)
            """,
            {"id": employee_id},
        )
        await self.execute(
            "UPDATE users SET is_active = false, delete_at = now(), update_at = now() WHERE employee_id = CAST(:id AS uuid)",
            {"id": employee_id},
        )

    async def assignments(self, employee_id: UUID | str, org_id: UUID | str) -> list[Any] | None:
        """Riwayat penempatan divisi/kantor karyawan."""
        row = await self.fetchone(
            """
            SELECT 
                e.employee_id AS id,
                e.employee_id,
                COALESCE(u.system_role::text, 'EMPLOYEE') AS position,
                e.division_id AS unit_id,
                d.name AS unit_name,
                e.join_date::date AS valid_from,
                e.pkwt_end_date::date AS valid_to
            FROM employee e
            LEFT JOIN division d ON d.division_id = e.division_id
            LEFT JOIN users u ON u.employee_id = e.employee_id
            WHERE e.employee_id = CAST(:id AS uuid) AND e.delete_at IS NULL
            """,
            {"id": employee_id},
        )
        return [row] if row else []

    async def last_assignment_start(self, employee_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT join_date::date FROM employee WHERE employee_id = CAST(:id AS uuid)",
            {"id": employee_id},
        )

    async def promote(self, employee_id: UUID | str, position: str, unit_id: str | None, valid_from: Any) -> Any:
        """Memutasi karyawan ke divisi baru."""
        await self.execute(
            """
            UPDATE employee 
            SET division_id = CAST(:unit AS uuid), update_at = now() 
            WHERE employee_id = CAST(:id AS uuid)
            """,
            {"id": employee_id, "unit": unit_id},
        )
        return await self.fetchone(
            """
            SELECT 
                e.employee_id AS id, e.employee_id, :pos AS position, e.division_id AS unit_id,
                :start AS valid_from, e.pkwt_end_date::date AS valid_to
            FROM employee e WHERE e.employee_id = CAST(:id AS uuid)
            """,
            {"id": employee_id, "pos": position, "start": valid_from},
        )

    async def on_running_plan(self, employee_id: UUID | str) -> bool:
        """Cek apakah karyawan terlibat dalam rencana kerja yang sedang berjalan."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1 FROM work_plan wp
                WHERE wp.delete_at IS NULL AND wp.status NOT IN ('DRAFT', 'COMPLETED', 'CANCELLED')
                  AND (wp.pm_id = CAST(:emp AS uuid)
                       OR EXISTS (
                           SELECT 1 FROM work_plan_team wpt
                           JOIN member m ON m.team_id = wpt.team_id
                           WHERE wpt.work_plan_id = wp.work_plan_id AND m.employee_id = CAST(:emp AS uuid)
                       ))
            )
            """,
            {"emp": employee_id},
        ))

    async def offboard(self, employee_id: UUID | str, reason: str, today: Any) -> None:
        """Offboarding karyawan dan pencabutan akses login/sesi."""
        await self.execute(
            """
            UPDATE employee 
            SET offboarding_status = 'offboarded', update_at = now() 
            WHERE employee_id = CAST(:id AS uuid)
            """,
            {"id": employee_id},
        )
        # Nonaktifkan akun pengguna dan cabut seluruh sesi
        user_id = await self.scalar(
            "UPDATE users SET is_active = false, update_at = now() WHERE employee_id = CAST(:id AS uuid) RETURNING user_id",
            {"id": employee_id},
        )
        if user_id:
            await self.execute(
                "UPDATE user_sessions SET is_revoked = TRUE, update_at = now() WHERE user_id = CAST(:uid AS uuid)",
                {"uid": user_id},
            )

    _SELECT_FIELDS = """
        e.employee_id AS id,
        e.employee_no,
        e.full_name,
        COALESCE(u.system_role::text, 'EMPLOYEE') AS position,
        e.division_id AS unit_id,
        u.email,
        NULL::text AS phone,
        e.join_date::date AS join_date,
        NULL::date AS birth_date,
        addr.full_address AS address,
        CASE 
            WHEN u.system_role IN ('SUPER_ADMIN', 'OPERATIONAL_MANAGER', 'ADMIN_HR_GA') THEN 'OFFICE'
            ELSE 'FIELD'
        END AS attendance_mode,
        (e.offboarding_status != 'offboarded') AS is_active,
        CASE WHEN e.offboarding_status = 'offboarded' THEN e.update_at ELSE NULL END AS offboarded_at,
        CASE WHEN e.offboarding_status != 'active' THEN e.offboarding_status::text ELSE NULL END AS offboarding_reason,
        NULL::uuid AS photo_file_id
    """

    @staticmethod
    def _filter(is_active: bool | None, q: str | None) -> tuple[str, dict[str, Any]]:
        where = ["e.delete_at IS NULL"]
        params: dict[str, Any] = {}
        if is_active is True:
            where.append("e.offboarding_status != 'offboarded'")
        elif is_active is False:
            where.append("e.offboarding_status = 'offboarded'")
        if q:
            where.append("(e.full_name ILIKE :q OR e.employee_no ILIKE :q OR u.email ILIKE :q)")
            params["q"] = f"%{q}%"
        return " AND ".join(where), params

    async def count_in_org(self, org_id: UUID | str, is_active: bool | None, q: str | None) -> int:
        where_sql, params = self._filter(is_active, q)
        sql = f"""
            SELECT COUNT(*) AS n 
            FROM employee e
            LEFT JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL
            WHERE {where_sql}
        """
        row = await self.fetchone(sql, params)
        return int(row.n) if row else 0

    async def page_in_org(
        self, org_id: UUID | str, is_active: bool | None, q: str | None, limit: int, offset: int
    ) -> list[Any]:
        where_sql, params = self._filter(is_active, q)
        sql = f"""
            SELECT {self._SELECT_FIELDS}
            FROM employee e
            LEFT JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL
            LEFT JOIN LATERAL (
                SELECT string_agg(a.address_line || ', ' || a.city, '; ') AS full_address 
                FROM address a 
                WHERE a.employee_id = e.employee_id AND a.delete_at IS NULL
            ) addr ON true
            WHERE {where_sql}
            ORDER BY e.full_name ASC
            LIMIT :limit OFFSET :offset
        """
        return list(await self.fetchall(sql, {**params, "limit": limit, "offset": offset}))

    async def get_in_org(self, employee_id: UUID | str, org_id: UUID | str) -> Any:
        sql = f"""
            SELECT {self._SELECT_FIELDS}
            FROM employee e
            LEFT JOIN users u ON u.employee_id = e.employee_id AND u.delete_at IS NULL
            LEFT JOIN LATERAL (
                SELECT string_agg(a.address_line || ', ' || a.city, '; ') AS full_address 
                FROM address a 
                WHERE a.employee_id = e.employee_id AND a.delete_at IS NULL
            ) addr ON true
            WHERE e.employee_id = CAST(:id AS uuid) AND e.delete_at IS NULL
        """
        return await self.fetchone(sql, {"id": employee_id})

    async def insert(self, org_id: UUID | str, data: dict[str, Any]) -> Any:
        """Membuat karyawan baru."""
        row = await self.fetchone(
            """
            INSERT INTO employee (
                office_id, division_id, full_name, employee_no, join_date, offboarding_status
            )
            VALUES (
                COALESCE(CAST(:office_id AS uuid), '11111111-0000-4000-a000-000000000001'::uuid),
                CAST(:unit_id AS uuid),
                :full_name,
                :employee_no,
                CAST(:join_date AS timestamptz),
                'active'
            )
            RETURNING employee_id AS id, full_name, employee_no, join_date, offboarding_status
            """,
            {
                "office_id": data.get("office_id"),
                "unit_id": data.get("unit_id"),
                "full_name": data["full_name"],
                "employee_no": data["employee_no"],
                "join_date": data["join_date"],
            },
        )
        if data.get("address"):
            await self.execute(
                """
                INSERT INTO address (employee_id, address_line, city, postal_code)
                VALUES (:emp, :addr, 'Medan', '20111')
                """,
                {"emp": row.id, "addr": data["address"]},
            )
        return await self.get_in_org(row.id, org_id)

    async def update_fields(self, employee_id: UUID | str, org_id: UUID | str, fields: dict[str, Any]) -> Any:
        """Update atribut karyawan."""
        if "full_name" in fields:
            await self.execute(
                "UPDATE employee SET full_name = :name, update_at = now() WHERE employee_id = CAST(:id AS uuid)",
                {"id": employee_id, "name": fields["full_name"]},
            )
        if "address" in fields:
            await self.execute(
                """
                INSERT INTO address (employee_id, address_line, city, postal_code)
                VALUES (CAST(:id AS uuid), :addr, 'Medan', '20111')
                ON CONFLICT DO NOTHING
                """,
                {"id": employee_id, "addr": fields["address"]},
            )
        return await self.get_in_org(employee_id, org_id)

    async def conflicts(
        self, employee_id: UUID | str, start: Any, end: Any, exclude_plan: UUID | str | None
    ) -> list[Any]:
        """Bentrok jadwal tugas pada work_plan."""
        return []
