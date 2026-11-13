"""
api/app/modules/hse/repositories/vehicle_inspection_repository.py

Repositori basis data untuk inspeksi keselamatan kendaraan kerja lapangan.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, escape_like
from app.modules.hse.schemas.hse_schema import VehicleInspectionCreate, VehicleInspectionVerify


class VehicleInspectionRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create(self, data: VehicleInspectionCreate, inspector_id: UUID) -> dict[str, Any]:
        query = """
            INSERT INTO vehicle_safety_inspections (
                vehicle_id, inspector_id, period_type, inspection_date,
                odometer_km, checklist_json, photos_json, notes, status
            )
            VALUES (
                :vehicle_id, :inspector_id, :period_type, COALESCE(:inspection_date, CURRENT_DATE),
                :odometer_km, CAST(:checklist_json AS jsonb), CAST(:photos_json AS jsonb), :notes, 'SUBMITTED'
            )
            RETURNING
                inspection_id, vehicle_id, inspector_id, period_type,
                inspection_date, odometer_km, checklist_json, photos_json,
                notes, status, verified_by_id, verified_at, create_at;
        """
        params = {
            "vehicle_id": data.vehicle_id,
            "inspector_id": inspector_id,
            "period_type": data.period_type,
            "inspection_date": data.inspection_date,
            "odometer_km": data.odometer_km,
            "checklist_json": json.dumps(data.checklist_json),
            "photos_json": json.dumps(data.photos_json),
            "notes": data.notes,
        }
        row = await self.fetchone(query, params)
        return dict(row._mapping) if row else {}

    async def get_by_id(self, inspection_id: UUID) -> dict[str, Any] | None:
        query = """
            SELECT
                i.inspection_id, i.vehicle_id, v.name AS vehicle_name, v.number_plate, v.office_id,
                i.inspector_id, e.full_name AS inspector_name,
                i.period_type, i.inspection_date, i.odometer_km,
                i.checklist_json, i.photos_json, i.notes, i.status,
                i.verified_by_id, COALESCE(ve.full_name, vu.email) AS verifier_name,
                i.verified_at, i.create_at
            FROM vehicle_safety_inspections i
            JOIN vehicle v ON v.vehicle_id = i.vehicle_id
            JOIN employee e ON e.employee_id = i.inspector_id
            LEFT JOIN users vu ON vu.user_id = i.verified_by_id
            LEFT JOIN employee ve ON ve.employee_id = vu.employee_id
            WHERE i.inspection_id = :inspection_id AND i.delete_at IS NULL;
        """
        row = await self.fetchone(query, {"inspection_id": inspection_id})
        return dict(row._mapping) if row else None

    async def list_inspections(
        self,
        vehicle_id: UUID | None = None,
        period_type: str | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 50,
        offset: int = 0,
        offices: list[str] | None = None,
        q: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Satu kueri: baris halaman + total (COUNT OVER). Nomor baris dihitung di SQL, tanpa memuat sisanya."""
        conditions = ["i.delete_at IS NULL"]
        params: dict[str, Any] = {"first": offset, "last": offset + limit}

        if vehicle_id:
            conditions.append("i.vehicle_id = :vehicle_id")
            params["vehicle_id"] = vehicle_id
        if period_type:
            conditions.append("i.period_type = :period_type")
            params["period_type"] = period_type
        if status:
            conditions.append("i.status = :status")
            params["status"] = status
        if from_date:
            conditions.append("i.inspection_date >= :from_date")
            params["from_date"] = from_date
        if to_date:
            conditions.append("i.inspection_date <= :to_date")
            params["to_date"] = to_date
        if q:  # awalan: plat, nama kendaraan, nama pemeriksa
            conditions.append(
                "(v.number_plate ILIKE :q_prefix || '%' ESCAPE '\' OR v.name ILIKE :q_prefix || '%' ESCAPE '\'"
                " OR e.full_name ILIKE :q_prefix || '%' ESCAPE '\')"
            )
            params["q_prefix"] = escape_like(q)

        if offices is not None:  # peran HSE tambahan: hanya kendaraan di kantor penugasan (ADR 0002 fase 2)
            conditions.append("v.office_id = ANY(CAST(:offices AS uuid[]))")
            params["offices"] = offices

        where_clause = " AND ".join(conditions)
        query = f"""
            WITH page AS (
                SELECT
                    i.inspection_id, i.vehicle_id, v.name AS vehicle_name, v.number_plate, v.office_id,
                    i.inspector_id, e.full_name AS inspector_name,
                    i.period_type, i.inspection_date, i.odometer_km,
                    i.checklist_json, i.photos_json, i.notes, i.status,
                    i.verified_by_id, COALESCE(ve.full_name, vu.email) AS verifier_name,
                    i.verified_at, i.create_at,
                    COUNT(*) OVER () AS total_count,
                    ROW_NUMBER() OVER (ORDER BY i.inspection_date DESC, i.create_at DESC, i.inspection_id) AS rn
                FROM vehicle_safety_inspections i
                JOIN vehicle v ON v.vehicle_id = i.vehicle_id
                JOIN employee e ON e.employee_id = i.inspector_id
                LEFT JOIN users vu ON vu.user_id = i.verified_by_id
                LEFT JOIN employee ve ON ve.employee_id = vu.employee_id
                WHERE {where_clause}
            )
            SELECT
                inspection_id, vehicle_id, vehicle_name, number_plate, office_id,
                inspector_id, inspector_name, period_type, inspection_date, odometer_km,
                checklist_json, photos_json, notes, status,
                verified_by_id, verifier_name, verified_at, create_at, total_count
            FROM page
            WHERE rn > :first AND rn <= :last
            ORDER BY rn;
        """
        rows = [dict(r._mapping) for r in await self.fetchall(query, params)]
        total = int(rows[0]["total_count"]) if rows else await self._count_total(where_clause, params)
        for r in rows:
            r.pop("total_count", None)
        return rows, total

    async def _count_total(self, where_clause: str, params: dict[str, Any]) -> int:
        """Halaman melewati ujung data: hitung total tersendiri agar X-Total-Count tetap benar."""
        count_params = {k: v for k, v in params.items() if k not in ("first", "last")}
        value = await self.scalar(
            f"""
            SELECT COUNT(*)
            FROM vehicle_safety_inspections i
            JOIN vehicle v ON v.vehicle_id = i.vehicle_id
            JOIN employee e ON e.employee_id = i.inspector_id
            WHERE {where_clause}
            """,
            count_params,
        )
        return int(value or 0)

    async def vehicle_office(self, vehicle_id: UUID) -> tuple[bool, str | None]:
        """(kendaraan aktif ada?, kantornya)."""
        row = await self.fetchone(
            "SELECT CAST(office_id AS text) AS office_id FROM vehicle WHERE vehicle_id = :vid AND delete_at IS NULL",
            {"vid": vehicle_id},
        )
        if row is None:
            return False, None
        return True, (str(row.office_id) if row.office_id else None)

    async def verify(
        self,
        inspection_id: UUID,
        data: VehicleInspectionVerify,
        verifier_id: UUID,
    ) -> dict[str, Any] | None:
        query = """
            UPDATE vehicle_safety_inspections
            SET
                status = :status,
                notes = COALESCE(CAST(:notes AS TEXT), notes),
                verified_by_id = :verifier_id,
                verified_at = NOW(),
                update_at = NOW()
            WHERE inspection_id = :inspection_id AND delete_at IS NULL
            RETURNING inspection_id;
        """
        params = {
            "inspection_id": inspection_id,
            "status": data.status,
            "notes": data.notes,
            "verifier_id": verifier_id,
        }
        row = await self.fetchone(query, params)
        if not row:
            return None
        return await self.get_by_id(inspection_id)

