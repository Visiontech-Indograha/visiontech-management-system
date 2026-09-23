"""
app/repositories/attendance_repo.py
Query untuk attendance dan site.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class AttendanceRepo(BaseRepo):

    async def get_site(self, site_id: UUID, org_id: UUID) -> Any:
        return await self.fetchone(
            """
            SELECT id, name, address, radius_m,
                   location,
                   ST_Y(location::geometry) AS lat,
                   ST_X(location::geometry) AS lng
            FROM vms.site WHERE id = :site AND organization_id = :org AND deleted_at IS NULL
            """,
            {"site": site_id, "org": org_id},
        )

    async def distance_to_site(
        self,
        lat: float,
        lng: float,
        site_location: Any,
    ) -> float:
        """Hitung jarak (meter) antara titik dan lokasi site menggunakan PostGIS."""
        row = await self.fetchone(
            """
            SELECT ST_Distance(
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :site_loc
            ) AS dist
            """,
            {"lat": lat, "lng": lng, "site_loc": site_location},
        )
        return float(row.dist) if row else 0.0

    async def get_active_checkin(self, employee_id: UUID, work_date: date) -> Any:
        return await self.fetchone(
            """
            SELECT * FROM vms.attendance
            WHERE employee_id = :emp AND work_date = :wdate AND check_out_at IS NULL
            """,
            {"emp": employee_id, "wdate": work_date},
        )

    async def create_checkin(self, data: dict[str, Any]) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.attendance (
                organization_id, employee_id, work_date, site_id, site_label,
                check_in_at, location, location_origin, distance_m, radius_m,
                is_late, selfie_file_id, status, face_result, face_similarity
            ) VALUES (
                :org, :emp, :wdate, :site, :slabel, now(),
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :orig, :dist, :rad,
                :late, :file, :status, :f_res, :f_sim
            ) RETURNING *
            """,
            data,
        )

    async def update_checkout(self, att_id: UUID, is_early: bool, status: str) -> Any:
        return await self.fetchone(
            """
            UPDATE vms.attendance
            SET check_out_at = now(), is_early_leave = :early, status = :status
            WHERE id = :id RETURNING *
            """,
            {"early": is_early, "status": status, "id": att_id},
        )

    async def list_attendance(
        self,
        org_id: UUID,
        work_date_from: date | None = None,
        work_date_to: date | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Any]:
        where = "a.organization_id = :org"
        params: dict[str, Any] = {"org": org_id, "limit": limit}
        if work_date_from:
            where += " AND a.work_date >= :from_d"
            params["from_d"] = work_date_from
        if work_date_to:
            where += " AND a.work_date <= :to_d"
            params["to_d"] = work_date_to
        if status:
            where += " AND a.status = :status"
            params["status"] = status
        return await self.fetchall(
            f"""
            SELECT a.*, e.full_name, e.employee_no
            FROM vms.attendance a
            JOIN vms.employee e ON a.employee_id = e.id
            WHERE {where}
            ORDER BY a.work_date DESC, e.full_name ASC
            LIMIT :limit
            """,
            params,
        )
