"""
app/modules/offboarding/repositories/offboarding_repository.py
Repository akses basis data untuk tabel employee_offboarding dan offboarding_clearance_item.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase
from app.modules.offboarding.schemas.offboarding_schema import (
    ClearanceItemVerify,
    OffboardingCreate,
)


class OffboardingRepository(CRUDBase):
    """Akses query untuk data offboarding karyawan dan clearance aset."""

    async def list_offboardings(self, status: str | None = None) -> Sequence[Any]:
        sql = """
            SELECT
                o.offboarding_id,
                o.employee_id,
                o.reason_type::text AS reason_type,
                o.submission_date,
                o.effective_date,
                o.is_all_assets_returned,
                o.approved_by_pm_id,
                o.approved_by_hr_id,
                o.status,
                o.notes,
                o.create_at,
                e.full_name AS employee_name,
                e.employee_no,
                d.name AS division_name
            FROM employee_offboarding o
            JOIN employee e ON e.employee_id = o.employee_id
            LEFT JOIN division d ON d.division_id = e.division_id
            WHERE o.delete_at IS NULL
        """
        params: dict[str, Any] = {}
        if status:
            sql += " AND o.status = :status"
            params["status"] = status
        sql += " ORDER BY o.submission_date DESC"
        return await self.fetchall(sql, params)

    async def get_offboarding_by_id(self, offboarding_id: UUID) -> Any | None:
        sql = """
            SELECT
                o.offboarding_id,
                o.employee_id,
                o.reason_type::text AS reason_type,
                o.submission_date,
                o.effective_date,
                o.is_all_assets_returned,
                o.approved_by_pm_id,
                o.approved_by_hr_id,
                o.status,
                o.notes,
                o.create_at,
                e.full_name AS employee_name,
                e.employee_no,
                d.name AS division_name
            FROM employee_offboarding o
            JOIN employee e ON e.employee_id = o.employee_id
            LEFT JOIN division d ON d.division_id = e.division_id
            WHERE o.offboarding_id = :id AND o.delete_at IS NULL
        """
        return await self.fetchone(sql, {"id": offboarding_id})

    async def list_clearance_items(self, offboarding_id: UUID) -> Sequence[Any]:
        sql = """
            SELECT
                c.clearance_item_id,
                c.offboarding_id,
                c.assignment_id,
                c.return_condition,
                c.handover_photo_path,
                c.verified_by_id,
                c.verified_at,
                c.create_at,
                a.asset_type,
                COALESCE(v.name, t.name, 'Aset Lain') AS asset_name,
                e.full_name AS verified_by_name
            FROM offboarding_clearance_item c
            JOIN asset_assignment a ON a.assignment_id = c.assignment_id
            LEFT JOIN vehicle v ON v.vehicle_id = a.vehicle_id
            LEFT JOIN tool t ON t.tool_id = a.tool_id
            LEFT JOIN employee e ON e.employee_id = c.verified_by_id
            WHERE c.offboarding_id = :id AND c.delete_at IS NULL
            ORDER BY c.create_at ASC
        """
        return await self.fetchall(sql, {"id": offboarding_id})

    async def create_offboarding(self, data: OffboardingCreate) -> Any:
        offboarding_id = uuid.uuid4()
        sql = """
            INSERT INTO employee_offboarding (
                offboarding_id, employee_id, reason_type, submission_date,
                effective_date, is_all_assets_returned, status, notes,
                create_at, update_at
            ) VALUES (
                :id, :emp_id, CAST(:reason AS offboarding_reason_enum), NOW(),
                :eff_date, false, 'active', :notes,
                NOW(), NOW()
            )
            RETURNING offboarding_id
        """
        await self.execute(sql, {
            "id": offboarding_id,
            "emp_id": data.employee_id,
            "reason": data.reason_type.value,
            "eff_date": data.effective_date,
            "notes": data.notes,
        })

        # Otomatis deteksi aset yang masih dipegang karyawan di asset_assignment dan buat clearance_item
        find_assets_sql = """
            SELECT assignment_id FROM asset_assignment
            WHERE employee_id = :emp_id AND returned_at IS NULL AND delete_at IS NULL
        """
        active_assets = await self.fetchall(find_assets_sql, {"emp_id": data.employee_id})
        for asset in active_assets:
            clearance_id = uuid.uuid4()
            insert_item_sql = """
                INSERT INTO offboarding_clearance_item (
                    clearance_item_id, offboarding_id, assignment_id, return_condition,
                    create_at, update_at
                ) VALUES (
                    :cid, :oid, :aid, 'PENDING_CHECK', NOW(), NOW()
                )
            """
            await self.execute(insert_item_sql, {
                "cid": clearance_id,
                "oid": offboarding_id,
                "aid": asset.assignment_id,
            })

        return await self.get_offboarding_by_id(offboarding_id)

    async def verify_clearance_item(
        self, clearance_item_id: UUID, verifier_id: UUID, data: ClearanceItemVerify
    ) -> Any | None:
        sql = """
            UPDATE offboarding_clearance_item
            SET return_condition = :cond,
                handover_photo_path = :photo,
                verified_by_id = :vid,
                verified_at = NOW(),
                update_at = NOW()
            WHERE clearance_item_id = :id AND delete_at IS NULL
            RETURNING offboarding_id, assignment_id
        """
        res = await self.fetchone(sql, {
            "id": clearance_item_id,
            "cond": data.return_condition,
            "photo": data.handover_photo_path,
            "vid": verifier_id,
        })
        if res:
            # Update asset_assignment returned_at
            update_asset_sql = """
                UPDATE asset_assignment
                SET returned_at = NOW(),
                    return_condition = :cond,
                    update_at = NOW()
                WHERE assignment_id = :aid
            """
            await self.execute(update_asset_sql, {
                "aid": res.assignment_id,
                "cond": data.return_condition,
            })

            # Cek apakah semua clearance item sudah diverifikasi
            check_all_sql = """
                SELECT COUNT(*)::int AS pending_count
                FROM offboarding_clearance_item
                WHERE offboarding_id = :oid AND verified_at IS NULL AND delete_at IS NULL
            """
            pending = await self.fetchone(check_all_sql, {"oid": res.offboarding_id})
            if pending and pending.pending_count == 0:
                await self.execute("""
                    UPDATE employee_offboarding
                    SET is_all_assets_returned = true, update_at = NOW()
                    WHERE offboarding_id = :oid
                """, {"oid": res.offboarding_id})

        return res

    async def approve_offboarding(
        self, offboarding_id: UUID, approval_type: str, approver_id: UUID
    ) -> Any | None:
        if approval_type.upper() == "PM":
            sql = """
                UPDATE employee_offboarding
                SET approved_by_pm_id = :aid, status = 'in_process', update_at = NOW()
                WHERE offboarding_id = :id AND delete_at IS NULL
            """
        else:
            sql = """
                UPDATE employee_offboarding
                SET approved_by_hr_id = :aid, status = 'offboarded', update_at = NOW()
                WHERE offboarding_id = :id AND delete_at IS NULL
            """
        await self.execute(sql, {"id": offboarding_id, "aid": approver_id})
        return await self.get_offboarding_by_id(offboarding_id)
