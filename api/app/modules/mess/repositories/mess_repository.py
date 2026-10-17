"""
app/modules/mess/repositories/mess_repository.py
Repository akses basis data untuk tabel company_mess_stay.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.crud.base import CRUDBase
from app.modules.mess.schemas.mess_schema import MessStayCreate, MessStayUpdate


class MessRepository(CRUDBase):
    """Akses query untuk data hunian mess karyawan."""

    async def list_stays(self, employee_id: UUID | None = None, weekly_plan_id: UUID | None = None) -> Sequence[Any]:
        sql = """
            SELECT
                m.mess_stay_id,
                m.mess_name,
                m.city,
                m.address,
                m.latitude,
                m.longitude,
                m.employee_id,
                m.weekly_plan_id,
                m.stay_start_date,
                m.stay_end_date,
                m.create_at,
                e.full_name AS employee_name,
                e.employee_no
            FROM company_mess_stay m
            JOIN employee e ON e.employee_id = m.employee_id
            WHERE m.delete_at IS NULL
        """
        params: dict[str, Any] = {}
        if employee_id:
            sql += " AND m.employee_id = :emp_id"
            params["emp_id"] = employee_id
        if weekly_plan_id:
            sql += " AND m.weekly_plan_id = :wp_id"
            params["wp_id"] = weekly_plan_id
        sql += " ORDER BY m.stay_start_date DESC"
        return await self.fetchall(sql, params)

    async def get_stay_by_id(self, mess_stay_id: UUID) -> Any | None:
        sql = """
            SELECT
                m.mess_stay_id,
                m.mess_name,
                m.city,
                m.address,
                m.latitude,
                m.longitude,
                m.employee_id,
                m.weekly_plan_id,
                m.stay_start_date,
                m.stay_end_date,
                m.create_at,
                e.full_name AS employee_name,
                e.employee_no
            FROM company_mess_stay m
            JOIN employee e ON e.employee_id = m.employee_id
            WHERE m.mess_stay_id = :mess_stay_id AND m.delete_at IS NULL
        """
        return await self.fetchone(sql, {"mess_stay_id": mess_stay_id})

    async def create_stay(self, data: MessStayCreate) -> Any:
        stay_id = uuid.uuid4()
        sql = """
            INSERT INTO company_mess_stay (
                mess_stay_id, mess_name, city, address, latitude, longitude,
                employee_id, weekly_plan_id, stay_start_date, stay_end_date,
                create_at, update_at
            ) VALUES (
                :stay_id, :mess_name, :city, :address, :lat, :lng,
                :emp_id, :wp_id, :start_date, :end_date,
                NOW(), NOW()
            )
            RETURNING mess_stay_id
        """
        await self.execute(sql, {
            "stay_id": stay_id,
            "mess_name": data.mess_name,
            "city": data.city,
            "address": data.address,
            "lat": data.latitude,
            "lng": data.longitude,
            "emp_id": data.employee_id,
            "wp_id": data.weekly_plan_id,
            "start_date": data.stay_start_date,
            "end_date": data.stay_end_date,
        })
        return await self.get_stay_by_id(stay_id)

    async def update_stay(self, mess_stay_id: UUID, data: MessStayUpdate) -> Any | None:
        updates: list[str] = ["update_at = NOW()"]
        params: dict[str, Any] = {"mess_stay_id": mess_stay_id}
        if data.mess_name is not None:
            updates.append("mess_name = :mess_name")
            params["mess_name"] = data.mess_name
        if data.city is not None:
            updates.append("city = :city")
            params["city"] = data.city
        if data.address is not None:
            updates.append("address = :address")
            params["address"] = data.address
        if data.latitude is not None:
            updates.append("latitude = :lat")
            params["lat"] = data.latitude
        if data.longitude is not None:
            updates.append("longitude = :lng")
            params["lng"] = data.longitude
        if data.stay_start_date is not None:
            updates.append("stay_start_date = :start_date")
            params["start_date"] = data.stay_start_date
        if data.stay_end_date is not None:
            updates.append("stay_end_date = :end_date")
            params["end_date"] = data.stay_end_date

        set_clause = ", ".join(updates)
        sql = (
            f"UPDATE company_mess_stay SET {set_clause} "
            "WHERE mess_stay_id = :mess_stay_id AND delete_at IS NULL"
        )
        await self.execute(sql, params)
        return await self.get_stay_by_id(mess_stay_id)

    async def delete_stay(self, mess_stay_id: UUID) -> bool:
        sql = "UPDATE company_mess_stay SET delete_at = NOW() WHERE mess_stay_id = :mess_stay_id AND delete_at IS NULL"
        await self.execute(sql, {"mess_stay_id": mess_stay_id})
        return True
