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

    async def list_with_state(self, org_id: UUID | str) -> list[Any]:
        """Aset organisasi + alokasi yang sedang berjalan + pengajuan pengembalian yang menunggu (R-19)."""
        return list(await self.fetchall(
            """
            SELECT a.*, al.id AS allocation_id, al.work_plan_id, wp.number AS plan_number,
                   wp.leader_employee_id, r.id AS pending_return_id, r.condition_on_return AS return_condition,
                   r.note AS return_note, re.full_name AS return_requested_by_name
            FROM vms.asset a
            LEFT JOIN vms.asset_allocation al ON al.asset_id = a.id AND al.released_at IS NULL
            LEFT JOIN vms.work_plan wp ON wp.id = al.work_plan_id
            LEFT JOIN LATERAL (SELECT * FROM vms.asset_return x
                               WHERE x.asset_allocation_id = al.id AND x.verified_at IS NULL
                               ORDER BY x.requested_at DESC LIMIT 1) r ON true
            LEFT JOIN vms.employee re ON re.id = r.requested_by
            WHERE a.organization_id = :org AND a.deleted_at IS NULL
            ORDER BY a.name
            """,
            {"org": org_id}))

    _RETURN_ROWS = """
        SELECT r.id, r.requested_at, r.verified_at, r.condition_on_return, r.note, r.is_accepted,
               rq.full_name AS requested_by_name, vf.full_name AS verified_by_name,
               wp.number AS plan_number, wp.title AS plan_title, al.allocated_at, dr.full_name AS driver_name,
               a.id AS asset_id, a.name AS asset_name, a.code AS asset_code, CAST(a.kind AS text) AS asset_kind,
               a.vehicle_type
        FROM vms.asset_return r
        JOIN vms.asset_allocation al ON al.id = r.asset_allocation_id
        JOIN vms.asset a ON a.id = al.asset_id
        JOIN vms.work_plan wp ON wp.id = al.work_plan_id
        JOIN vms.employee rq ON rq.id = r.requested_by
        LEFT JOIN vms.employee vf ON vf.id = r.verified_by
        LEFT JOIN vms.employee dr ON dr.id = al.driver_employee_id
    """

    async def return_history(self, asset_id: UUID | str, org_id: UUID | str) -> list[Any] | None:
        """Riwayat pengembalian aset (terbaru dulu). None bila aset bukan milik organisasi ini."""
        if not await self.scalar("SELECT 1 FROM vms.asset WHERE id = :id AND organization_id = :org",
                                 {"id": asset_id, "org": org_id}):
            return None
        return list(await self.fetchall(self._RETURN_ROWS + " WHERE a.id = :id ORDER BY r.requested_at DESC",
                                        {"id": asset_id}))

    async def return_record(self, return_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(self._RETURN_ROWS + " WHERE r.id = :id AND a.organization_id = :org",
                                   {"id": return_id, "org": org_id})

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
