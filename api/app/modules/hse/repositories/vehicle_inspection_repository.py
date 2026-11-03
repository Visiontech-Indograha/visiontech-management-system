"""
api/app/modules/hse/repositories/vehicle_inspection_repository.py

Repositori basis data untuk inspeksi keselamatan kendaraan kerja lapangan.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.hse.schemas import VehicleInspectionCreate, VehicleInspectionVerify


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
                i.inspection_id, i.vehicle_id, v.name AS vehicle_name, v.number_plate,
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
    ) -> Sequence[dict[str, Any]]:
        conditions = ["i.delete_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

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

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT
                i.inspection_id, i.vehicle_id, v.name AS vehicle_name, v.number_plate,
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
            WHERE {where_clause}
            ORDER BY i.inspection_date DESC, i.create_at DESC
            LIMIT :limit OFFSET :offset;
        """
        rows = await self.fetchall(query, params)
        return [dict(r._mapping) for r in rows]

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
                notes = CASE WHEN :notes IS NOT NULL THEN :notes ELSE notes END,
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

