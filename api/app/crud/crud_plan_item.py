"""
app/crud/crud_plan_item.py
Repository akses basis data untuk entitas work_plan_item.
Menerapkan kueri SQL statis (bukan f-string), parameter terikat ANSI CAST(:x AS tipe),
penyaringan soft delete (WHERE delete_at IS NULL), dan pencocokan jsonb array.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from app.crud.base import CRUDBase


class CRUDPlanItem(CRUDBase):
    """Operasi database untuk item rencana kerja harian (work_plan_item)."""

    async def check_employee_conflicts(
        self,
        work_date: date,
        start_time: str,
        end_time: str,
        employee_ids: list[UUID],
        exclude_item_id: UUID | None = None,
    ) -> list[Any]:
        """Memeriksa tabrakan jadwal teknisi pada slot waktu tertentu di hari kerja yang sama."""
        if not employee_ids:
            return []

        # Memeriksa item aktif lain yang jadwalnya overlap
        query = """
        SELECT
            i.item_id,
            i.title,
            CAST(i.start_time AS varchar) AS start_time,
            CAST(i.end_time AS varchar) AS end_time,
            e.employee_id,
            e.full_name
        FROM work_plan_item i
        JOIN work_plan_daily d ON d.daily_plan_id = i.daily_plan_id AND d.delete_at IS NULL
        CROSS JOIN unnest(CAST(:emp_ids AS uuid[])) AS target_emp(id)
        JOIN employee e ON e.employee_id = target_emp.id AND e.delete_at IS NULL
        WHERE i.delete_at IS NULL
          AND d.work_date = CAST(:work_date AS date)
          AND (CAST(:exclude_id AS uuid) IS NULL OR i.item_id != CAST(:exclude_id AS uuid))
          AND i.status NOT IN ('DONE', 'CANCELLED', 'ROLLED_OVER')
          AND i.start_time IS NOT NULL AND i.end_time IS NOT NULL
          AND (i.start_time < CAST(:end_time AS time) AND i.end_time > CAST(:start_time AS time))
          AND i.assigned_employee_ids @> to_jsonb(target_emp.id::text)
        """
        emp_id_strs = "{" + ",".join(str(eid) for eid in employee_ids) + "}"
        rows = await self.fetchall(
            query,
            {
                "work_date": work_date,
                "start_time": start_time,
                "end_time": end_time,
                "emp_ids": emp_id_strs,
                "exclude_id": str(exclude_item_id) if exclude_item_id else None,
            },
        )
        return list(rows)

    async def check_vehicle_conflicts(
        self,
        work_date: date,
        start_time: str,
        end_time: str,
        vehicle_id: UUID,
        exclude_item_id: UUID | None = None,
    ) -> list[Any]:
        """Memeriksa tabrakan jadwal pemakaian armada/kendaraan."""
        query = """
        SELECT
            aa.assignment_id,
            aa.vehicle_id,
            v.plate_number,
            i.item_id,
            i.title,
            CAST(i.start_time AS varchar) AS start_time,
            CAST(i.end_time AS varchar) AS end_time
        FROM asset_assignment aa
        JOIN vehicle v ON v.vehicle_id = aa.vehicle_id AND v.delete_at IS NULL
        JOIN work_plan_daily d ON d.daily_plan_id = aa.daily_plan_id AND d.delete_at IS NULL
        JOIN work_plan_item i ON i.daily_plan_id = d.daily_plan_id AND i.delete_at IS NULL
        WHERE aa.delete_at IS NULL
          AND aa.vehicle_id = CAST(:vehicle_id AS uuid)
          AND d.work_date = CAST(:work_date AS date)
          AND (CAST(:exclude_id AS uuid) IS NULL OR i.item_id != CAST(:exclude_id AS uuid))
          AND i.status NOT IN ('DONE', 'CANCELLED', 'ROLLED_OVER')
          AND i.start_time IS NOT NULL AND i.end_time IS NOT NULL
          AND (i.start_time < CAST(:end_time AS time) AND i.end_time > CAST(:start_time AS time))
        """
        rows = await self.fetchall(
            query,
            {
                "work_date": work_date,
                "start_time": start_time,
                "end_time": end_time,
                "vehicle_id": str(vehicle_id),
                "exclude_id": str(exclude_item_id) if exclude_item_id else None,
            },
        )
        return list(rows)

    async def update_progress(
        self,
        item_id: UUID,
        completed_qty: float | None = None,
        progress_percent: float | None = None,
        status: str | None = None,
        delay_reason: str | None = None,
    ) -> Any:
        """Memperbarui capaian aktual dan persentase penyelesaian tugas."""
        query = """
        UPDATE work_plan_item
        SET
            completed_qty = COALESCE(CAST(:completed_qty AS numeric), completed_qty),
            progress_percent = COALESCE(CAST(:progress_percent AS numeric), progress_percent),
            status = CASE
                WHEN CAST(:progress_percent AS numeric) >= 100 THEN 'DONE'
                WHEN :status IS NOT NULL THEN :status
                ELSE status
            END,
            delay_reason = COALESCE(:delay_reason, delay_reason),
            update_at = NOW()
        WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
        RETURNING item_id, completed_qty, progress_percent, status, delay_reason
        """
        return await self.fetchone(
            query,
            {
                "item_id": str(item_id),
                "completed_qty": completed_qty,
                "progress_percent": progress_percent,
                "status": status,
                "delay_reason": delay_reason,
            },
        )

    async def request_rollover(
        self,
        item_id: UUID,
        delay_reason: str,
        target_daily_plan_id: UUID | None = None,
    ) -> Any:
        """Mengajukan pemindahan tugas ke status PENDING_ROLLOVER menunggu persetujuan PM."""
        query = """
        UPDATE work_plan_item
        SET
            status = 'PENDING_ROLLOVER',
            rollover_approval_status = 'WAITING_PM'::rollover_approval_enum,
            delay_reason = :delay_reason,
            shifted_to_daily_id = CAST(:target_daily_id AS uuid),
            update_at = NOW()
        WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
        RETURNING item_id, status, rollover_approval_status::text AS rollover_approval_status,
                  delay_reason, shifted_to_daily_id
        """
        return await self.fetchone(
            query,
            {
                "item_id": str(item_id),
                "delay_reason": delay_reason,
                "target_daily_id": str(target_daily_plan_id) if target_daily_plan_id else None,
            },
        )

    async def approve_rollover(
        self,
        item_id: UUID,
        pm_employee_id: UUID,
        pm_override_reason: str,
        target_daily_plan_id: UUID,
    ) -> Any:
        """Menyetujui pemindahan tugas dan membuat tugas lanjutan otomatis di hari tujuan."""
        # 1. Update tugas asal menjadi SHIFTED_DAY
        update_query = """
        UPDATE work_plan_item
        SET
            status = 'SHIFTED_DAY',
            rollover_approval_status = 'APPROVED_BY_PM'::rollover_approval_enum,
            approved_by_pm_id = CAST(:pm_id AS uuid),
            shifted_to_daily_id = CAST(:target_daily_id AS uuid),
            delay_reason = :pm_reason,
            update_at = NOW()
        WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
        RETURNING item_id, weekly_plan_id, work_type_id, title, target_qty, completed_qty,
                  completion_id, start_time, end_time, location_name, site_lat, site_lng, assigned_employee_ids
        """
        original = await self.fetchone(
            update_query,
            {
                "item_id": str(item_id),
                "pm_id": str(pm_employee_id),
                "target_daily_id": str(target_daily_plan_id),
                "pm_reason": pm_override_reason,
            },
        )
        if not original:
            return None

        # 2. Sisipkan klon tugas ke hari tujuan dengan sisa volume
        rem_qty = max(0.0, float(original.target_qty or 0) - float(original.completed_qty or 0))
        if rem_qty <= 0:
            rem_qty = float(original.target_qty or 1.0)

        insert_query = """
        INSERT INTO work_plan_item (
            daily_plan_id, weekly_plan_id, work_type_id, title,
            target_qty, completed_qty, progress_percent, status,
            rollover_approval_status, origin_item_id, completion_id,
            start_time, end_time, location_name, site_lat, site_lng, assigned_employee_ids
        )
        VALUES (
            CAST(:target_daily_id AS uuid),
            (SELECT weekly_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:target_daily_id AS uuid)),
            CAST(:work_type_id AS uuid),
            :title,
            CAST(:rem_qty AS numeric),
            0.0,
            0.0,
            'PLANNED',
            'NONE'::rollover_approval_enum,
            CAST(:origin_id AS uuid),
            CAST(:completion_id AS uuid),
            CAST(:start_time AS time),
            CAST(:end_time AS time),
            :location_name,
            CAST(:site_lat AS numeric),
            CAST(:site_lng AS numeric),
            CAST(:assigned_emp_ids AS jsonb)
        )
        RETURNING item_id
        """
        emp_ids_json = (
            json.dumps(original.assigned_employee_ids)
            if original.assigned_employee_ids
            else None
        )
        new_row = await self.fetchone(
            insert_query,
            {
                "target_daily_id": str(target_daily_plan_id),
                "work_type_id": str(original.work_type_id),
                "title": f"[Lanjutan] {original.title}",
                "rem_qty": rem_qty,
                "origin_id": str(item_id),
                "completion_id": str(original.completion_id) if original.completion_id else None,
                "start_time": str(original.start_time) if original.start_time else None,
                "end_time": str(original.end_time) if original.end_time else None,
                "location_name": original.location_name,
                "site_lat": original.site_lat,
                "site_lng": original.site_lng,
                "assigned_emp_ids": emp_ids_json,
            },
        )
        return {"original": original, "new_item_id": new_row.item_id if new_row else None}

    async def reject_rollover(
        self,
        item_id: UUID,
        pm_employee_id: UUID,
        pm_override_reason: str,
    ) -> Any:
        """Menolak pemindahan tugas, mengembalikan status ke TODO."""
        query = """
        UPDATE work_plan_item
        SET
            status = 'TODO',
            rollover_approval_status = 'REJECTED_BY_PM'::rollover_approval_enum,
            approved_by_pm_id = CAST(:pm_id AS uuid),
            delay_reason = :pm_reason,
            update_at = NOW()
        WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
        RETURNING item_id, status, rollover_approval_status::text AS rollover_approval_status
        """
        return await self.fetchone(
            query,
            {
                "item_id": str(item_id),
                "pm_id": str(pm_employee_id),
                "pm_reason": pm_override_reason,
            },
        )

    async def move_slot(
        self,
        item_id: UUID,
        pm_employee_id: UUID,
        pm_override_reason: str,
        target_daily_plan_id: UUID | None = None,
        target_start_time: str | None = None,
        target_end_time: str | None = None,
        new_status: str | None = None,
    ) -> Any:
        """Memindahkan tugas secara langsung ke slot lain (PM Full Override)."""
        query = """
        UPDATE work_plan_item
        SET
            daily_plan_id = COALESCE(CAST(:target_daily_id AS uuid), daily_plan_id),
            weekly_plan_id = COALESCE(
                (SELECT weekly_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:target_daily_id AS uuid)),
                weekly_plan_id
            ),
            start_time = COALESCE(CAST(:start_time AS time), start_time),
            end_time = COALESCE(CAST(:end_time AS time), end_time),
            status = COALESCE(:new_status, status),
            delay_reason = :pm_reason,
            approved_by_pm_id = CAST(:pm_id AS uuid),
            update_at = NOW()
        WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
        RETURNING item_id, status, rollover_approval_status::text AS rollover_approval_status
        """
        return await self.fetchone(
            query,
            {
                "item_id": str(item_id),
                "target_daily_id": str(target_daily_plan_id) if target_daily_plan_id else None,
                "start_time": target_start_time,
                "end_time": target_end_time,
                "new_status": new_status,
                "pm_reason": pm_override_reason,
                "pm_id": str(pm_employee_id),
            },
        )
