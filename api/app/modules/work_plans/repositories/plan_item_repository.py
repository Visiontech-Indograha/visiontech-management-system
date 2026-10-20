"""
app/modules/work_plans/repositories/plan_item_repository.py
Repository akses basis data untuk entitas work_plan_item.
Menerapkan kueri SQL statis (bukan f-string), parameter terikat ANSI CAST(:x AS tipe),
penyaringan soft delete (WHERE delete_at IS NULL), dan pencocokan jsonb array.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import CRUDBase


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

    async def get_item_prerequisite(self, item_id: UUID) -> tuple[UUID | None, str | None, str | None]:
        """Mengecek apakah item memiliki prasyarat dan status tugas prasyarat tersebut."""
        sql = """
        SELECT
            p.item_id AS parent_id,
            p.title AS parent_title,
            p.status AS parent_status
        FROM work_plan_item i
        JOIN work_plan_item p ON p.item_id = i.depends_on_item_id
        WHERE i.item_id = CAST(:item_id AS uuid)
          AND i.delete_at IS NULL
          AND p.delete_at IS NULL
        """
        row = await self.fetchone(sql, {"item_id": str(item_id)})
        if not row:
            return None, None, None
        return row.parent_id, row.parent_title, str(row.parent_status)

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
                WHEN CAST(:status AS varchar) IS NOT NULL THEN CAST(:status AS varchar)
                ELSE status
            END,
            delay_reason = COALESCE(CAST(:delay_reason AS text), delay_reason),
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
        # 1. Ambil data asli tugas
        orig = await self.fetchone(
            """
            SELECT item_id, work_type_id, title, target_qty, completed_qty,
                   task_phase, is_main_deliverable, depends_on_item_id,
                   origin_item_id, completion_id, start_time, end_time, location_name,
                   site_lat, site_lng, assigned_employee_ids
            FROM work_plan_item
            WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
            """,
            {"item_id": str(item_id)},
        )
        if not orig:
            return None

        # 2. Ambil informasi hari tujuan
        target_day = await self.fetchone(
            """
            SELECT daily_plan_id, work_date, division_id, team_id
            FROM work_plan_daily
            WHERE daily_plan_id = CAST(:target_daily_id AS uuid) AND delete_at IS NULL
            """,
            {"target_daily_id": str(target_daily_plan_id)},
        )
        if not target_day:
            return None

        new_status = "SHIFTED_DAY"

        # 3. Update tugas asal
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
        RETURNING item_id, status, rollover_approval_status::text AS rollover_approval_status
        """
        updated_orig = await self.fetchone(
            update_query,
            {
                "item_id": str(item_id),
                "pm_id": str(pm_employee_id),
                "target_daily_id": str(target_daily_plan_id),
                "pm_reason": pm_override_reason,
            },
        )
        if not updated_orig:
            return None

        # 4. Sisipkan klon tugas ke hari tujuan dengan sisa volume
        rem_qty = max(0.0, float(orig.target_qty or 0) - float(orig.completed_qty or 0))
        if rem_qty <= 0:
            rem_qty = float(orig.target_qty or 1.0)

        # Root origin ID: pastikan selalu menunjuk ke akar tugas pertama (root item)
        root_origin_id = orig.origin_item_id or orig.item_id

        clean_title = orig.title
        new_title = (
            f"[Lanjutan] {clean_title}"
            if not clean_title.startswith("[Lanjutan]")
            else clean_title
        )

        insert_query = """
        INSERT INTO work_plan_item (
            daily_plan_id, work_type_id, title,
            task_phase, is_main_deliverable, depends_on_item_id,
            target_qty, completed_qty, progress_percent, status,
            rollover_approval_status, origin_item_id, completion_id,
            start_time, end_time, location_name, site_lat, site_lng, assigned_employee_ids
        )
        VALUES (
            CAST(:target_daily_id AS uuid),
            CAST(:work_type_id AS uuid),
            :title,
            :task_phase,
            :is_main_deliverable,
            CAST(:depends_on_id AS uuid),
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
            json.dumps(orig.assigned_employee_ids)
            if orig.assigned_employee_ids
            else None
        )
        start_t = orig.start_time
        if isinstance(start_t, str):
            from datetime import time as dt_time
            start_t = dt_time.fromisoformat(start_t)
        end_t = orig.end_time
        if isinstance(end_t, str):
            from datetime import time as dt_time
            end_t = dt_time.fromisoformat(end_t)

        new_row = await self.fetchone(
            insert_query,
            {
                "target_daily_id": str(target_daily_plan_id),
                "work_type_id": str(orig.work_type_id),
                "title": new_title,
                "task_phase": orig.task_phase or "MAIN_INSTALLATION",
                "is_main_deliverable": bool(orig.is_main_deliverable),
                "depends_on_id": str(orig.depends_on_item_id) if orig.depends_on_item_id else None,
                "rem_qty": rem_qty,
                "origin_id": str(root_origin_id),
                "completion_id": str(orig.completion_id) if orig.completion_id else None,
                "start_time": start_t,
                "end_time": end_t,
                "location_name": orig.location_name,
                "site_lat": orig.site_lat,
                "site_lng": orig.site_lng,
                "assigned_emp_ids": emp_ids_json,
            },
        )
        return {
            "original": orig,
            "new_item_id": new_row.item_id if new_row else None,
            "status": new_status,
            "is_cross_week": False,
        }

    async def get_task_chain_status(self, item_id: UUID) -> dict[str, Any] | None:
        """Mengambil status agregasi rantai tugas (task chain) dari tugas induk dan seluruh item turunannya."""
        # Cari root item id
        root_query = """
        WITH RECURSIVE item_ancestor AS (
            SELECT item_id, origin_item_id, 1 AS depth
            FROM work_plan_item
            WHERE item_id = CAST(:item_id AS uuid) AND delete_at IS NULL
            UNION ALL
            SELECT p.item_id, p.origin_item_id, a.depth + 1
            FROM work_plan_item p
            JOIN item_ancestor a ON a.origin_item_id = p.item_id
            WHERE p.delete_at IS NULL
        )
        SELECT item_id AS root_id
        FROM item_ancestor
        WHERE origin_item_id IS NULL
        LIMIT 1
        """
        root_res = await self.fetchone(root_query, {"item_id": str(item_id)})
        root_id = root_res.root_id if root_res else item_id

        # Ambil seluruh keluarga rantai tugas
        chain_query = """
        WITH RECURSIVE item_family AS (
            SELECT wpi.item_id, wpi.origin_item_id, wpi.daily_plan_id,
                   wpd.work_date, wpi.title, wpi.task_phase, wpi.is_main_deliverable,
                   wpi.depends_on_item_id, wpi.target_qty, wpi.completed_qty,
                   wpi.progress_percent, wpi.status, wpi.completion_id,
                   wpi.realization_photos_json, wpi.create_at, 1 AS lvl
            FROM work_plan_item wpi
            LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
            WHERE wpi.item_id = CAST(:root_id AS uuid) AND wpi.delete_at IS NULL
            UNION ALL
            SELECT c.item_id, c.origin_item_id, c.daily_plan_id,
                   d.work_date, c.title, c.task_phase, c.is_main_deliverable,
                   c.depends_on_item_id, c.target_qty, c.completed_qty,
                   c.progress_percent, c.status, c.completion_id,
                   c.realization_photos_json, c.create_at, f.lvl + 1
            FROM work_plan_item c
            LEFT JOIN work_plan_daily d ON d.daily_plan_id = c.daily_plan_id
            JOIN item_family f ON c.origin_item_id = f.item_id
            WHERE c.delete_at IS NULL
        )
        SELECT * FROM item_family ORDER BY lvl ASC, create_at ASC
        """
        family_rows = await self.fetchall(chain_query, {"root_id": str(root_id)})
        if not family_rows:
            return None

        # Filter deliverables murni untuk perhitungan akumulasi target dan capaian fisik
        deliverable_rows = [r for r in family_rows if bool(r.is_main_deliverable)]
        if not deliverable_rows:
            deliverable_rows = list(family_rows)

        initial_target = float(deliverable_rows[0].target_qty or 0.0)
        total_completed = sum(float(r.completed_qty or 0.0) for r in deliverable_rows)
        progress_pct = round((total_completed / initial_target * 100.0), 2) if initial_target > 0 else 0.0

        # Item aktif adalah item terakhir yang bukan SHIFTED_DAY
        active_items = [r for r in family_rows if r.status != "SHIFTED_DAY"]
        is_all_active_done = bool(active_items and all(r.status == "DONE" for r in active_items))
        is_eligible = bool(total_completed >= initial_target and is_all_active_done)

        status_label = (
            "SIAP DIBUAT WORK COMPLETION (100% SELESAI)"
            if is_eligible
            else "MASIH BERJALAN / BELUM SELESAI"
        )
        existing_comp = next((r.completion_id for r in family_rows if r.completion_id is not None), None)

        items_out = [
            {
                "item_id": r.item_id,
                "origin_item_id": r.origin_item_id,
                "daily_plan_id": r.daily_plan_id,
                "work_date": str(r.work_date) if r.work_date else None,
                "title": r.title,
                "task_phase": r.task_phase or "MAIN_INSTALLATION",
                "is_main_deliverable": bool(r.is_main_deliverable),
                "depends_on_item_id": r.depends_on_item_id,
                "target_qty": float(r.target_qty or 0.0),
                "completed_qty": float(r.completed_qty or 0.0),
                "progress_percent": float(r.progress_percent or 0.0),
                "status": str(r.status),
                "completion_id": r.completion_id,
                "realization_photos_json": r.realization_photos_json or [],
                "create_at": str(r.create_at) if r.create_at else None,
            }
            for r in family_rows
        ]

        return {
            "root_item_id": root_id,
            "initial_total_target": initial_target,
            "total_completed_across_weeks": total_completed,
            "total_progress_percent": progress_pct,
            "is_eligible_for_completion": is_eligible,
            "status_label": status_label,
            "existing_completion_id": existing_comp,
            "all_linked_item_ids": [r.item_id for r in family_rows],
            "items": items_out,
        }

    async def generate_completion_from_chain(
        self,
        item_id: UUID,
        pm_employee_id: UUID | None,
        client_name: str | None = None,
        project_title: str | None = None,
    ) -> dict[str, Any] | None:
        """Mengompilasi seluruh rantai tugas yang telah selesai 100% ke dalam dokumen work_completion."""
        chain = await self.get_task_chain_status(item_id)
        if not chain:
            return None

        all_ids = chain["all_linked_item_ids"]
        root_id = chain["root_item_id"]
        total_target = int(chain["initial_total_target"])
        total_completed = int(chain["total_completed_across_weeks"])

        meta = await self.fetchone(
            """
            SELECT wpi.title, wpi.completion_id, wpd.division_id,
                   wpd.daily_plan_id, d.pm_id,
                   MIN(wpd.work_date) AS min_date,
                   MAX(wpd.work_date) AS max_date
            FROM work_plan_item wpi
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
            JOIN division d ON d.division_id = wpd.division_id
            WHERE wpi.item_id = CAST(:root_id AS uuid)
            GROUP BY wpi.title, wpi.completion_id, wpd.division_id, wpd.daily_plan_id, d.pm_id
            """,
            {"root_id": str(root_id)},
        )
        if not meta:
            return None

        dates_res = await self.fetchall(
            """
            SELECT wpd.work_date
            FROM work_plan_item wpi
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
            WHERE wpi.item_id = ANY(CAST(:ids AS uuid[]))
            ORDER BY wpd.work_date ASC
            """,
            {"ids": [str(i) for i in all_ids]},
        )
        start_date = dates_res[0].work_date if dates_res else meta.min_date
        end_date = dates_res[-1].work_date if dates_res else meta.max_date

        if chain["existing_completion_id"]:
            comp_id = chain["existing_completion_id"]
            await self.execute(
                """
                UPDATE work_completion
                SET total_target_unit = CAST(:target AS integer),
                    order_status = 'COMPLETED',
                    start_work_date = CAST(:start_date AS date),
                    end_work_date = CAST(:end_date AS date),
                    summary_notes = :notes,
                    update_at = NOW()
                WHERE completion_id = CAST(:cid AS uuid) AND delete_at IS NULL
                """,
                {
                    "cid": str(comp_id),
                    "target": total_target,
                    "start_date": start_date,
                    "end_date": end_date,
                    "notes": (
                        f"Penyelesaian akumulasi tugas lintas jadwal "
                        f"({total_completed}/{total_target} unit tuntas 100%)."
                    ),
                },
            )
        else:
            c_name = client_name or "Klien Visiontech"
            p_title = project_title or meta.title
            notes = (
                f"Penyelesaian akumulasi tugas lintas jadwal ({total_completed}/{total_target} unit tuntas 100%) "
                f"melalui {len(all_ids)} tahapan kerja ({start_date} s/d {end_date})."
            )

            insert_comp = """
            INSERT INTO work_completion (
                report_scope, division_id, pm_id, client_name, project_title, order_number,
                total_target_unit, unit_measure, order_status, priority_level,
                summary_notes, obstacles, realization_photos_json,
                daily_plan_id, start_work_date, end_work_date
            )
            VALUES (
                'PROJECT',
                CAST(:div_id AS uuid),
                CAST(:pm_id AS uuid),
                :client_name,
                :project_title,
                NULL,
                CAST(:target AS integer),
                'Unit',
                'COMPLETED',
                'NORMAL',
                :notes,
                NULL,
                '[]'::jsonb,
                CAST(:daily_id AS uuid),
                CAST(:start_date AS date),
                CAST(:end_date AS date)
            )
            RETURNING completion_id
            """
            comp_row = await self.fetchone(
                insert_comp,
                {
                    "div_id": str(meta.division_id),
                    "pm_id": str(pm_employee_id or meta.pm_id),
                    "client_name": c_name,
                    "project_title": p_title,
                    "target": total_target,
                    "notes": notes,
                    "daily_id": str(meta.daily_plan_id),
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            comp_id = comp_row.completion_id

        for i_id in all_ids:
            await self.execute(
                """
                UPDATE work_plan_item
                SET completion_id = CAST(:cid AS uuid),
                    update_at = NOW()
                WHERE item_id = CAST(:iid AS uuid) AND delete_at IS NULL
                """,
                {"cid": str(comp_id), "iid": str(i_id)},
            )

        return {
            "success": True,
            "completion_id": comp_id,
            "total_target_unit": total_target,
            "order_status": "COMPLETED",
            "message": f"Work Completion ({comp_id}) berhasil dibuat dan ditautkan ke {len(all_ids)} item tugas.",
        }

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
