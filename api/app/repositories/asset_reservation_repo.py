"""
app/repositories/asset_reservation_repo.py
Reservasi aset per SK (V-27) — padanan `domain.js` RESERVE_ASSET, RELEASE_ASSET, CHECK_ASSET.
Satu baris `asset_allocation` terbuka (released_at NULL) = aset sedang dipesan/dipakai SK itu.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class AssetReservationRepo(BaseRepo):

    async def lock_asset(self, asset_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, CAST(kind AS text) AS kind, CAST(status AS text) AS status
            FROM vms.asset WHERE id = :id AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": asset_id},
        )

    async def plan_for_driver(self, plan_id: UUID | str, driver_id: UUID | str | None) -> Any:
        """Status SK dan apakah pengemudi bagian dari tim penugasan yang berlaku."""
        return await self.fetchone(
            """
            SELECT CAST(wp.status AS text) AS status,
                   wp.leader_employee_id = CAST(:driver AS uuid) OR EXISTS (
                       SELECT 1 FROM vms.work_plan_member m
                        WHERE m.work_plan_id = wp.id AND m.employee_id = CAST(:driver AS uuid)
                          AND upper_inf(m.valid_period)) AS driver_on_team
            FROM vms.work_plan wp WHERE wp.id = :plan
            """,
            {"plan": plan_id, "driver": driver_id},
        )

    async def active_allocation(self, asset_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT al.id, al.work_plan_id, al.driver_employee_id, al.driver_checked_at,
                   CAST(wp.status AS text) AS plan_status
            FROM vms.asset_allocation al JOIN vms.work_plan wp ON wp.id = al.work_plan_id
            WHERE al.asset_id = :asset AND al.released_at IS NULL
            """,
            {"asset": asset_id},
        )

    async def insert_allocation(self, asset_id: UUID | str, plan_id: UUID | str, driver_id: UUID | str | None,
                                user_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.asset_allocation (asset_id, work_plan_id, driver_employee_id, allocated_by)
            VALUES (:asset, :plan, :driver, (SELECT employee_id FROM vms.app_user WHERE id = :uid))
            RETURNING *
            """,
            {"asset": asset_id, "plan": plan_id, "driver": driver_id, "uid": user_id},
        )

    async def set_asset_status(self, asset_id: UUID | str, status: str) -> None:
        await self.execute(
            "UPDATE vms.asset SET status = CAST(:status AS vms.asset_status), updated_at = now() WHERE id = :id",
            {"id": asset_id, "status": status})

    async def free_asset(self, asset_id: UUID | str, allocation_id: UUID | str, condition: str | None) -> None:
        """domain.js freeAsset: reservasi ditutup, aset tersedia lagi (kondisi dicatat bila ada banding)."""
        await self.execute("UPDATE vms.asset_allocation SET released_at = now() WHERE id = :id",
                           {"id": allocation_id})
        await self.execute(
            """
            UPDATE vms.asset SET status = 'AVAILABLE', condition = COALESCE(:condition, condition), updated_at = now()
             WHERE id = :id
            """,
            {"id": asset_id, "condition": condition})

    async def mark_checked(self, allocation_id: UUID | str) -> None:
        await self.execute("UPDATE vms.asset_allocation SET driver_checked_at = now() WHERE id = :id",
                           {"id": allocation_id})

    async def employee_of(self, user_id: UUID | str) -> str | None:
        employee: str | None = await self.scalar(
            "SELECT CAST(employee_id AS text) FROM vms.app_user WHERE id = :uid", {"uid": user_id})
        return employee
