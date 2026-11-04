"""
app/modules/work_completion/repositories/work_completion_core_repository.py
Query inti entitas Work Completion (Order Klien) Master V3.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository, escape_like


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, dict):
        return row
    return dict(row)


# Pekerja lapangan (ketua tim maupun anggota) melihat order yang itemnya ada di jadwal tim mereka yang sudah disetujui.
FIELD_SCOPE = """EXISTS (
    SELECT 1 FROM work_plan_item fi
    JOIN work_plan_daily fd ON fd.daily_plan_id = fi.daily_plan_id AND fd.delete_at IS NULL
         AND fd.status IN ('APPROVED', 'ONGOING', 'COMPLETED')
    JOIN team ft ON ft.team_id = fd.team_id AND ft.delete_at IS NULL
    LEFT JOIN member fm ON fm.team_id = fd.team_id AND fm.is_active AND fm.delete_at IS NULL
    WHERE fi.completion_id = wc.completion_id AND fi.delete_at IS NULL
      AND (ft.leader_employee_id = CAST(:field AS uuid) OR fm.employee_id = CAST(:field AS uuid))
)"""


class WorkCompletionCoreRepository(BaseRepository):
    """Akses data dasar Order Proyek Klien."""

    async def standing(self, completion_id: UUID | str, employee_id: UUID | str | None) -> Any:
        """Kedudukan pengguna atas order: pengelola (PM order / PM-OM divisi) atau anggota tim jadwalnya."""
        return await self.fetchone(
            f"""
            SELECT wc.completion_id,
                   (CAST(:emp AS uuid) IS NOT NULL AND (wc.pm_id = CAST(:emp AS uuid) OR EXISTS (
                        SELECT 1 FROM division sd WHERE sd.division_id = wc.division_id
                        AND CAST(:emp AS uuid) IN (sd.pm_id, sd.om_id)))) AS manages,
                   (CAST(:emp AS uuid) IS NOT NULL AND {FIELD_SCOPE.replace(":field", ":emp")}) AS on_team
            FROM work_completion wc
            WHERE wc.completion_id = CAST(:id AS uuid) AND wc.delete_at IS NULL
            """,
            {"id": str(completion_id), "emp": str(employee_id) if employee_id else None},
        )

    async def client_snapshot(self, client_id: UUID | str) -> Any:
        """Klien dari master (sumber tunggal nama klien pada order)."""
        return await self.fetchone(
            "SELECT client_id, name FROM client WHERE client_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(client_id)},
        )

    async def project_snapshot(self, project_id: UUID | str) -> Any:
        """Data proyek untuk mengisi order: divisi, status, klien, judul, SPK, target."""
        return await self.fetchone(
            "SELECT p.division_id, p.status, p.pm_id, p.client_id, c.name AS client_name, "
            "p.project_title, p.spk_number, "
            "p.total_target_qty, p.unit_measure, p.start_date, p.end_date FROM project p "
            "JOIN client c ON c.client_id = p.client_id WHERE p.project_id = CAST(:id AS uuid) AND p.delete_at IS NULL",
            {"id": str(project_id)},
        )

    async def employee_role(self, employee_id: UUID | str) -> str | None:
        role: str | None = await self.scalar(
            "SELECT u.system_role::text FROM employee e JOIN users u ON u.employee_id = e.employee_id "
            "AND u.delete_at IS NULL AND u.is_active WHERE e.employee_id = CAST(:id AS uuid) "
            "AND e.delete_at IS NULL AND e.offboarding_status = 'active'",
            {"id": str(employee_id)},
        )
        return role

    async def get_pm_divisions(self, employee_id: UUID | str) -> list[dict[str, str]]:
        """Divisi yang dipimpin PM (bisa lebih dari satu). Tanpa divisi yang dipimpin, pakai divisi profil karyawan."""
        rows = await self.fetchall(
            "SELECT division_id, name FROM division WHERE pm_id = CAST(:emp AS uuid) AND delete_at IS NULL "
            "ORDER BY name",
            {"emp": str(employee_id)},
        )
        if not rows:
            rows = await self.fetchall(
                "SELECT d.division_id, d.name FROM employee e JOIN division d ON d.division_id = e.division_id "
                "WHERE e.employee_id = CAST(:emp AS uuid) AND e.delete_at IS NULL AND d.delete_at IS NULL",
                {"emp": str(employee_id)},
            )
        return [{"division_id": str(r.division_id), "name": r.name} for r in rows]

    async def is_division_manager(self, division_id: UUID | str, employee_id: UUID | str) -> bool:
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1 FROM division
                WHERE division_id = CAST(:division_id AS uuid)
                  AND delete_at IS NULL
                  AND CAST(:employee_id AS uuid) IN (pm_id, om_id)
            )
            """,
            {"division_id": str(division_id), "employee_id": str(employee_id)},
        ))

    async def is_division_pm(self, division_id: UUID | str, employee_id: UUID | str) -> bool:
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1 FROM division
                WHERE division_id = CAST(:division_id AS uuid)
                  AND delete_at IS NULL
                  AND pm_id = CAST(:employee_id AS uuid)
            )
            """,
            {"division_id": str(division_id), "employee_id": str(employee_id)},
        ))

    async def list_completions(
        self,
        *,
        division_id: UUID | str | None = None,
        status: str | None = None,
        search: str | None = None,
        pm_id: UUID | str | None = None,
        field_employee: UUID | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Membaca daftar order proyek klien dengan agregasi progres unit."""
        filters = ["wc.delete_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if division_id:
            filters.append("wc.division_id = CAST(:div_id AS uuid)")
            params["div_id"] = str(division_id)

        if status:
            filters.append("wc.order_status = :status")
            params["status"] = status

        if pm_id:
            filters.append(
                "(wc.pm_id = CAST(:pm_id AS uuid) OR EXISTS (SELECT 1 FROM division sd WHERE sd.division_id = "
                "wc.division_id AND CAST(:pm_id AS uuid) IN (sd.pm_id, sd.om_id)))"
            )
            params["pm_id"] = str(pm_id)

        if field_employee:
            filters.append(FIELD_SCOPE)
            params["field"] = str(field_employee)

        if search:
            search_clause = (
                "(wc.client_name ILIKE :search OR wc.project_title ILIKE :search OR wc.order_number ILIKE :search)"
            )
            filters.append(search_clause)
            params["search"] = f"%{escape_like(search)}%"

        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT
                wc.completion_id,
                wc.project_id,
                wc.division_id,
                d.name AS division_name,
                wc.pm_id,
                e_pm.full_name AS pm_name,
                wc.client_id,
                COALESCE(c.name, wc.client_name) AS client_name,
                wc.project_title,
                wc.order_number,
                wc.total_target_unit,
                COALESCE((
                    SELECT SUM(wpi.completed_qty)::int
                    FROM work_plan_item wpi
                    WHERE wpi.completion_id = wc.completion_id
                      AND wpi.is_main_deliverable = TRUE
                      AND wpi.delete_at IS NULL
                ), 0) AS completed_target_unit,
                -- Jenis pekerjaan order & persen progres nyata (rata-rata dikerjakan/target per pekerjaan).
                ARRAY(SELECT DISTINCT wpi.task_phase::text FROM work_plan_item wpi
                      WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL) AS phases,
                (SELECT COALESCE(ROUND(AVG(CASE WHEN wpi.status = 'DONE' THEN 1
                        ELSE LEAST(COALESCE(wpi.completed_qty, 0) / NULLIF(wpi.target_qty, 0), 1) END) * 100), 0)::int
                   FROM work_plan_item wpi WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL
                   AND wpi.status <> 'SHIFTED_DAY'
                   AND NOT (wpi.task_phase = 'SURVEY' AND wpi.depends_on_item_id IS NOT NULL)) AS progress_pct,
                wc.unit_measure,
                wc.order_status,
                wc.priority_level,
                wc.acc_status,
                wc.acc_decided_at,
                wc.acc_decided_by_id,
                e_acc.full_name AS acc_decided_by_name,
                wc.acc_notes,
                COALESCE(wc.start_work_date, (
                    SELECT MIN(wpd.work_date)
                    FROM work_plan_item wpi
                    JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
                    WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL AND wpd.delete_at IS NULL
                )) AS start_work_date,
                COALESCE(wc.end_work_date, (
                    SELECT MAX(wpd.work_date)
                    FROM work_plan_item wpi
                    JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
                    WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL AND wpd.delete_at IS NULL
                )) AS end_work_date,
                wc.site_address,
                wc.site_lat::float AS site_lat,
                wc.site_lng::float AS site_lng,
                wc.summary_notes,
                wc.obstacles,
                wc.realization_photos_json,
                wc.leader_signer_id,
                e_ldr.full_name AS leader_signer_name,
                wc.leader_signed_at,
                wc.pm_signer_id,
                e_pm2.full_name AS pm_signer_name,
                wc.pm_signed_at,
                wc.signature_hash,
                wc.create_at,
                wc.update_at
            FROM work_completion wc
            LEFT JOIN division d ON d.division_id = wc.division_id
            LEFT JOIN client c ON c.client_id = wc.client_id
            LEFT JOIN employee e_pm ON e_pm.employee_id = wc.pm_id
            LEFT JOIN employee e_acc ON e_acc.employee_id = wc.acc_decided_by_id
            LEFT JOIN employee e_ldr ON e_ldr.employee_id = wc.leader_signer_id
            LEFT JOIN employee e_pm2 ON e_pm2.employee_id = wc.pm_signer_id
            WHERE {where_clause}
            ORDER BY
                CASE wc.priority_level
                    WHEN 'URGENT' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'NORMAL' THEN 3
                    ELSE 4
                END,
                wc.create_at DESC
            LIMIT :limit OFFSET :offset
        """
        rows = await self.fetchall(sql, params)
        return [_row_to_dict(r) for r in rows]

    async def count_completions(
        self,
        *,
        division_id: UUID | str | None = None,
        status: str | None = None,
        search: str | None = None,
        pm_id: UUID | str | None = None,
        field_employee: UUID | str | None = None,
    ) -> int:
        """Menghitung total baris order proyek untuk pagination."""
        filters = ["wc.delete_at IS NULL"]
        params: dict[str, Any] = {}

        if division_id:
            filters.append("wc.division_id = CAST(:div_id AS uuid)")
            params["div_id"] = str(division_id)

        if status:
            filters.append("wc.order_status = :status")
            params["status"] = status

        if pm_id:
            filters.append(
                "(wc.pm_id = CAST(:pm_id AS uuid) OR EXISTS (SELECT 1 FROM division sd WHERE sd.division_id = "
                "wc.division_id AND CAST(:pm_id AS uuid) IN (sd.pm_id, sd.om_id)))"
            )
            params["pm_id"] = str(pm_id)

        if field_employee:
            filters.append(FIELD_SCOPE)
            params["field"] = str(field_employee)

        if search:
            search_clause = (
                "(wc.client_name ILIKE :search OR wc.project_title ILIKE :search OR wc.order_number ILIKE :search)"
            )
            filters.append(search_clause)
            params["search"] = f"%{escape_like(search)}%"

        where_clause = " AND ".join(filters)
        sql = f"SELECT COUNT(*) FROM work_completion wc WHERE {where_clause}"
        count = await self.scalar(sql, params)
        return int(count or 0)

    async def get_completion(self, completion_id: UUID | str) -> dict[str, Any] | None:
        """Membaca detail satu order proyek klien."""
        sql = """
            SELECT
                wc.completion_id,
                wc.project_id,
                wc.division_id,
                d.name AS division_name,
                wc.pm_id,
                e_pm.full_name AS pm_name,
                wc.client_id,
                COALESCE(c.name, wc.client_name) AS client_name,
                wc.project_title,
                wc.order_number,
                wc.total_target_unit,
                COALESCE((
                    SELECT SUM(wpi.completed_qty)::int
                    FROM work_plan_item wpi
                    WHERE wpi.completion_id = wc.completion_id
                      AND wpi.is_main_deliverable = TRUE
                      AND wpi.delete_at IS NULL
                ), 0) AS completed_target_unit,
                wc.unit_measure,
                wc.order_status,
                wc.priority_level,
                wc.acc_status,
                wc.acc_decided_at,
                wc.acc_decided_by_id,
                e_acc.full_name AS acc_decided_by_name,
                wc.acc_notes,
                COALESCE(wc.start_work_date, (
                    SELECT MIN(wpd.work_date)
                    FROM work_plan_item wpi
                    JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
                    WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL AND wpd.delete_at IS NULL
                )) AS start_work_date,
                COALESCE(wc.end_work_date, (
                    SELECT MAX(wpd.work_date)
                    FROM work_plan_item wpi
                    JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
                    WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL AND wpd.delete_at IS NULL
                )) AS end_work_date,
                wc.site_address,
                wc.site_lat::float AS site_lat,
                wc.site_lng::float AS site_lng,
                wc.summary_notes,
                wc.obstacles,
                wc.realization_photos_json,
                COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'revision_id', r.revision_id,
                        'completion_id', r.completion_id,
                        'description', r.description,
                        'request_date', r.request_date,
                        'survey_task_id', r.survey_task_id,
                        'status', r.status,
                        'created_by_id', r.created_by_id,
                        'created_by_name', e_rev.full_name,
                        'create_at', r.create_at
                    ) ORDER BY r.create_at DESC)
                    FROM work_completion_revision r
                    LEFT JOIN employee e_rev ON e_rev.employee_id = r.created_by_id
                    WHERE r.completion_id = wc.completion_id AND r.delete_at IS NULL
                ), '[]'::jsonb) AS revisions,
                COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'bom_id', b.bom_id,
                        'completion_id', b.completion_id,
                        'work_plan_item_id', b.work_plan_item_id,
                        'material_code', b.material_code,
                        'material_name', b.material_name,
                        'estimated_qty', b.estimated_qty::float,
                        'actual_qty', b.actual_qty::float,
                        'unit', b.unit,
                        'category', b.category,
                        'notes', b.notes,
                        'sort_order', b.sort_order,
                        'create_at', b.create_at,
                        'update_at', b.update_at
                    ) ORDER BY b.sort_order, b.material_name)
                    FROM work_completion_bom b
                    WHERE b.completion_id = wc.completion_id AND b.delete_at IS NULL
                      AND COALESCE(b.category, 'MATERIAL') NOT IN ('KEBUTUHAN', 'KABEL')
                ), '[]'::jsonb) AS bom_items,
                wc.leader_signer_id,
                e_ldr.full_name AS leader_signer_name,
                wc.leader_signed_at,
                wc.leader_signature_path,
                wc.pm_signature_path,
                wc.pm_signer_id,
                e_pm2.full_name AS pm_signer_name,
                wc.pm_signed_at,
                wc.signature_hash,
                wc.create_at,
                wc.update_at
            FROM work_completion wc
            LEFT JOIN division d ON d.division_id = wc.division_id
            LEFT JOIN client c ON c.client_id = wc.client_id
            LEFT JOIN employee e_pm ON e_pm.employee_id = wc.pm_id
            LEFT JOIN employee e_acc ON e_acc.employee_id = wc.acc_decided_by_id
            LEFT JOIN employee e_ldr ON e_ldr.employee_id = wc.leader_signer_id
            LEFT JOIN employee e_pm2 ON e_pm2.employee_id = wc.pm_signer_id
            WHERE wc.completion_id = CAST(:id AS uuid) AND wc.delete_at IS NULL
        """
        row = await self.fetchone(sql, {"id": str(completion_id)})
        return _row_to_dict(row) if row else None

    async def create_completion(self, data: dict[str, Any]) -> str:
        """Membuat order proyek baru."""
        sql = """
            INSERT INTO work_completion (
                report_scope, division_id, pm_id, project_id, client_id, client_name, project_title, order_number,
                total_target_unit, unit_measure, order_status, priority_level, acc_status,
                site_address, site_lat, site_lng, summary_notes, realization_photos_json
            ) VALUES (
                COALESCE(:report_scope, 'PROJECT'),
                CAST(:division_id AS uuid),
                CAST(:pm_id AS uuid),
                CAST(:project_id AS uuid),
                CAST(:client_id AS uuid),
                :client_name,
                :project_title,
                :order_number,
                :total_target_unit,
                :unit_measure,
                :order_status,
                :priority_level,
                'MENUNGGU_ACC',
                :site_address,
                :site_lat,
                :site_lng,
                :summary_notes,
                CAST(:realization_photos_json AS jsonb)
            )
            RETURNING completion_id
        """
        photos = data.get("realization_photos_json") or []
        lat = data.get("site_lat")  # sudah divalidasi skema (rentang -90..90 / -180..180)
        lng = data.get("site_lng")

        res = await self.scalar(
            sql,
            {
                "report_scope": data.get("report_scope", "PROJECT"),
                "division_id": str(data["division_id"]),
                "pm_id": str(data["pm_id"]) if data.get("pm_id") else None,
                "project_id": str(data["project_id"]) if data.get("project_id") else None,
                "client_id": str(data["client_id"]) if data.get("client_id") else None,
                "client_name": data.get("client_name"),
                "project_title": data["project_title"],
                "order_number": data.get("order_number"),
                "total_target_unit": data.get("total_target_unit", 1),
                "unit_measure": data.get("unit_measure", "Unit"),
                "order_status": data.get("order_status", "ONGOING"),
                "priority_level": data.get("priority_level", "NORMAL"),
                "site_address": data.get("site_address"),
                "site_lat": lat,
                "site_lng": lng,
                "summary_notes": data.get("summary_notes") or "",
                "realization_photos_json": json.dumps(photos),
            },
        )
        return str(res)

    async def update_completion(self, completion_id: UUID | str, data: dict[str, Any],
                                *, expected_status: str | None = None) -> int:
        """Memperbarui rincian order proyek. `expected_status` (compare-and-set): UPDATE hanya berlaku bila status
        saat itu masih sama. Kembalian = jumlah baris yang berubah (0 = sudah diubah pihak lain atau dihapus)."""
        updates = ["update_at = NOW()"]
        params: dict[str, Any] = {"id": str(completion_id)}

        allowed_fields = [
            "client_id", "client_name", "project_title", "order_number", "total_target_unit",
            "unit_measure", "order_status", "priority_level", "site_address",
            "site_lat", "site_lng", "summary_notes",
        ]
        for k in allowed_fields:
            if k in data and data[k] is not None:
                updates.append(f"{k} = :{k}")
                params[k] = data[k]

        guard = ""
        if expected_status is not None:
            guard = " AND order_status = :expected"
            params["expected"] = expected_status
        set_clause = ", ".join(updates)
        sql = (f"UPDATE work_completion SET {set_clause} "
               f"WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL{guard}")
        result = await self.execute(sql, params)
        return int(result.rowcount or 0)

    async def update_status(self, completion_id: UUID | str, status: str, notes: str | None = None,
                            *, expected: str) -> int:
        """Memperbarui status order (PM override), hanya bila status saat itu masih `expected` (compare-and-set).
        Kembalian = jumlah baris yang berubah; 0 berarti status sudah diubah pihak lain."""
        sql = """
            UPDATE work_completion
            SET order_status = CAST(:status AS varchar),
                summary_notes = CASE
                    WHEN CAST(:notes AS text) IS NOT NULL
                    THEN COALESCE(summary_notes, '') || E'\n[Status ' || CAST(:status AS text) || ']: '
                         || CAST(:notes AS text)
                    ELSE summary_notes
                END,
                update_at = NOW()
            WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL AND order_status = :expected
        """
        result = await self.execute(
            sql, {"id": str(completion_id), "status": status, "notes": notes, "expected": expected})
        return int(result.rowcount or 0)

    async def delete_completion(self, completion_id: UUID | str) -> None:
        """Soft delete order proyek klien."""
        sql = """
            UPDATE work_completion
            SET delete_at = NOW(), update_at = NOW()
            WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        await self.execute(sql, {"id": str(completion_id)})
