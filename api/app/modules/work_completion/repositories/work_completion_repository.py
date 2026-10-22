"""
app/modules/work_completion/repositories/work_completion_repository.py

Akses data database untuk entitas Work Completion (Order Klien) Master V3.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, dict):
        return row
    return dict(row)


# Pekerja lapangan melihat order yang itemnya ada di jadwal tim mereka yang sudah disetujui.
FIELD_SCOPE = """EXISTS (
    SELECT 1 FROM work_plan_item fi
    JOIN work_plan_daily fd ON fd.daily_plan_id = fi.daily_plan_id AND fd.delete_at IS NULL
         AND fd.status IN ('APPROVED', 'ONGOING', 'COMPLETED')
    JOIN member fm ON fm.team_id = fd.team_id AND fm.is_active AND fm.delete_at IS NULL
    WHERE fi.completion_id = wc.completion_id AND fi.delete_at IS NULL AND fm.employee_id = CAST(:field AS uuid)
)"""


class WorkCompletionRepository(BaseRepository):
    """Akses data Order Proyek Klien (work_completion N─1 division, N─1 employee pm; 1─N work_plan_item)."""

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

    async def project_snapshot(self, project_id: UUID | str) -> Any:
        """Data proyek untuk mengisi order: divisi, status, klien, judul, SPK, target."""
        return await self.fetchone(
            "SELECT p.division_id, p.status, p.pm_id, c.name AS client_name, p.project_title, p.spk_number, "
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
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT
                wc.completion_id,
                wc.project_id,
                wc.division_id,
                d.name AS division_name,
                wc.pm_id,
                e_pm.full_name AS pm_name,
                wc.client_name,
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
            LEFT JOIN employee e_pm ON e_pm.employee_id = wc.pm_id
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
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(filters)
        sql = f"SELECT COUNT(*) FROM work_completion wc WHERE {where_clause}"
        res = await self.scalar(sql, params)
        return int(res or 0)

    async def get_completion(self, completion_id: UUID | str) -> dict[str, Any] | None:
        """Mengambil satu order proyek klien secara detail."""
        sql = """
            SELECT
                wc.completion_id,
                wc.project_id,
                wc.division_id,
                d.name AS division_name,
                wc.pm_id,
                e_pm.full_name AS pm_name,
                wc.client_name,
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
            LEFT JOIN employee e_pm ON e_pm.employee_id = wc.pm_id
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
                report_scope, division_id, pm_id, project_id, client_name, project_title, order_number,
                total_target_unit, unit_measure, order_status, priority_level,
                site_address, site_lat, site_lng, summary_notes, realization_photos_json
            ) VALUES (
                COALESCE(:report_scope, 'PROJECT'),
                CAST(:division_id AS uuid),
                CAST(:pm_id AS uuid),
                CAST(:project_id AS uuid),
                :client_name,
                :project_title,
                :order_number,
                :total_target_unit,
                :unit_measure,
                :order_status,
                :priority_level,
                :site_address,
                :site_lat,
                :site_lng,
                :summary_notes,
                CAST(:realization_photos_json AS jsonb)
            )
            RETURNING completion_id
        """
        photos = data.get("realization_photos_json") or []
        res = await self.scalar(
            sql,
            {
                "report_scope": data.get("report_scope", "PROJECT"),
                "division_id": str(data["division_id"]),
                "pm_id": str(data["pm_id"]) if data.get("pm_id") else None,
                "project_id": str(data["project_id"]) if data.get("project_id") else None,
                "client_name": data["client_name"],
                "project_title": data["project_title"],
                "order_number": data.get("order_number"),
                "total_target_unit": data.get("total_target_unit", 1),
                "unit_measure": data.get("unit_measure", "Unit"),
                "order_status": data.get("order_status", "ONGOING"),
                "priority_level": data.get("priority_level", "NORMAL"),
                "site_address": data.get("site_address"),
                "site_lat": data.get("site_lat"),
                "site_lng": data.get("site_lng"),
                "summary_notes": data.get("summary_notes") or "",  # DB uji: NOT NULL (DDL: NULL) — "" aman di keduanya
                "realization_photos_json": json.dumps(photos),
            },
        )
        return str(res)

    async def update_completion(self, completion_id: UUID | str, data: dict[str, Any]) -> None:
        """Memperbarui rincian order proyek."""
        updates = ["update_at = NOW()"]
        params: dict[str, Any] = {"id": str(completion_id)}

        allowed_fields = [
            "client_name", "project_title", "order_number", "total_target_unit",
            "unit_measure", "order_status", "priority_level", "site_address",
            "site_lat", "site_lng", "summary_notes",
        ]
        for k in allowed_fields:
            if k in data and data[k] is not None:
                updates.append(f"{k} = :{k}")
                params[k] = data[k]

        set_clause = ", ".join(updates)
        sql = f"UPDATE work_completion SET {set_clause} WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL"
        await self.execute(sql, params)

    async def update_status(self, completion_id: UUID | str, status: str, notes: str | None = None) -> None:
        """Memperbarui status order (PM override)."""
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
            WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        await self.execute(sql, {"id": str(completion_id), "status": status, "notes": notes})

    async def sign_completion(
        self,
        *,
        completion_id: UUID | str,
        signer_id: UUID | str,
        as_leader: bool,
        signature_key: str,
        summary_notes: str | None = None,
        obstacles: str | None = None,
        photos: list[str] | None = None,
    ) -> None:
        """Tanda tangan ketua (boleh diulang sebelum PM; sidik direset) atau PM (order selesai)."""
        if as_leader:
            sql = """
                UPDATE work_completion
                SET leader_signer_id = CAST(:signer_id AS uuid),
                    leader_signature_path = :sig_key,
                    leader_signed_at = NOW(),
                    summary_notes = COALESCE(:summary_notes, summary_notes),
                    obstacles = COALESCE(:obstacles, obstacles),
                    realization_photos_json = COALESCE(CAST(:photos AS jsonb), realization_photos_json),
                    signature_hash = NULL,
                    update_at = NOW()
                WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL AND pm_signed_at IS NULL
            """
        else:
            sql = """
                UPDATE work_completion
                SET pm_signer_id = CAST(:signer_id AS uuid),
                    pm_signature_path = :sig_key,
                    pm_signed_at = NOW(),
                    order_status = 'COMPLETED',
                    update_at = NOW()
                WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL AND pm_signed_at IS NULL
                  AND leader_signed_at IS NOT NULL
            """
        await self.execute(
            sql,
            {
                "id": str(completion_id),
                "signer_id": str(signer_id),
                "sig_key": signature_key,
                "summary_notes": summary_notes,
                "obstacles": obstacles,
                "photos": json.dumps(photos) if photos else None,
            },
        )

    async def remove_photo(self, completion_id: UUID | str, file_id: str) -> bool:
        """Lepas satu foto realisasi (format lama: id string; baru: {file_id}). True bila ada yang terhapus."""
        removed = await self.scalar(
            """
            UPDATE work_completion SET realization_photos_json = COALESCE((
                SELECT jsonb_agg(e) FROM jsonb_array_elements(realization_photos_json) e
                WHERE COALESCE(e->>'file_id', e #>> '{}') <> :f), '[]'::jsonb), update_at = now()
            WHERE completion_id = CAST(:id AS uuid)
              AND EXISTS (SELECT 1 FROM jsonb_array_elements(realization_photos_json) e
                          WHERE COALESCE(e->>'file_id', e #>> '{}') = :f)
            RETURNING 1
            """,
            {"id": str(completion_id), "f": file_id},
        )
        return bool(removed)

    async def set_signature_hash(self, completion_id: UUID | str, signature_hash: str) -> None:
        await self.execute(
            "UPDATE work_completion SET signature_hash = :h WHERE completion_id = CAST(:id AS uuid)",
            {"id": str(completion_id), "h": signature_hash},
        )

    async def existing_images(self, file_ids: list[str]) -> int:
        """Jumlah id yang benar-benar berkas gambar terunggah (foto realisasi BAST)."""
        if not file_ids:
            return 0
        count = await self.scalar(
            "SELECT COUNT(*) FROM file_object WHERE id = ANY(CAST(:ids AS uuid[])) AND mime_type LIKE 'image/%'",
            {"ids": file_ids},
        )
        return int(count or 0)

    async def list_bom_items(self, completion_id: UUID | str) -> list[dict[str, Any]]:
        """Daftar item BoM riil untuk satu order proyek klien."""
        sql = """
            SELECT
                bom_id,
                completion_id,
                work_plan_item_id,
                material_code,
                material_name,
                estimated_qty::float AS estimated_qty,
                actual_qty::float AS actual_qty,
                unit,
                category,
                notes,
                sort_order,
                create_at,
                update_at
            FROM work_completion_bom
            WHERE completion_id = CAST(:cid AS uuid) AND delete_at IS NULL
              -- survei: KEBUTUHAN (alat/izin) & KABEL (ukuran) bukan material BoM/BoQ
              AND COALESCE(category, 'MATERIAL') NOT IN ('KEBUTUHAN', 'KABEL')
            ORDER BY sort_order, material_name
        """
        rows = await self.fetchall(sql, {"cid": str(completion_id)})
        return [_row_to_dict(r) for r in rows]

    async def get_bom_item(self, bom_id: UUID | str) -> dict[str, Any] | None:
        """Satu item BoM."""
        sql = """
            SELECT
                bom_id,
                completion_id,
                work_plan_item_id,
                material_code,
                material_name,
                estimated_qty::float AS estimated_qty,
                actual_qty::float AS actual_qty,
                unit,
                category,
                notes,
                sort_order,
                create_at,
                update_at
            FROM work_completion_bom
            WHERE bom_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        row = await self.fetchone(sql, {"id": str(bom_id)})
        return _row_to_dict(row) if row else None

    async def add_bom_item(self, completion_id: UUID | str, data: dict[str, Any]) -> str:
        """Menambahkan item BoM baru ke order proyek klien."""
        sql = """
            INSERT INTO work_completion_bom (
                completion_id, work_plan_item_id, material_code, material_name,
                estimated_qty, actual_qty, unit, category, notes, sort_order
            )
            VALUES (
                CAST(:cid AS uuid),
                CAST(:item_id AS uuid),
                :code,
                :name,
                CAST(:est_qty AS numeric),
                CAST(:act_qty AS numeric),
                :unit,
                :category,
                :notes,
                CAST(:sort AS smallint)
            )
            RETURNING bom_id
        """
        res = await self.scalar(
            sql,
            {
                "cid": str(completion_id),
                "item_id": str(data["work_plan_item_id"]) if data.get("work_plan_item_id") else None,
                "code": data.get("material_code"),
                "name": data["material_name"],
                "est_qty": data.get("estimated_qty", 0.0),
                "act_qty": data.get("actual_qty", 0.0),
                "unit": data.get("unit", "Unit"),
                "category": data.get("category"),
                "notes": data.get("notes"),
                "sort": data.get("sort_order", 0),
            },
        )
        return str(res)

    async def update_bom_item(self, bom_id: UUID | str, data: dict[str, Any]) -> None:
        """Memperbarui item BoM (misal: pengisian pemakaian aktual di lapangan)."""
        updates: list[str] = ["update_at = NOW()"]
        params: dict[str, Any] = {"id": str(bom_id)}

        if "work_plan_item_id" in data:
            updates.append("work_plan_item_id = CAST(:item_id AS uuid)")
            params["item_id"] = str(data["work_plan_item_id"]) if data["work_plan_item_id"] else None
        if "material_code" in data:
            updates.append("material_code = :code")
            params["code"] = data["material_code"]
        if "material_name" in data and data["material_name"] is not None:
            updates.append("material_name = :name")
            params["name"] = data["material_name"]
        if "estimated_qty" in data and data["estimated_qty"] is not None:
            updates.append("estimated_qty = CAST(:est_qty AS numeric)")
            params["est_qty"] = data["estimated_qty"]
        if "actual_qty" in data and data["actual_qty"] is not None:
            updates.append("actual_qty = CAST(:act_qty AS numeric)")
            params["act_qty"] = data["actual_qty"]
        if "unit" in data and data["unit"] is not None:
            updates.append("unit = :unit")
            params["unit"] = data["unit"]
        if "category" in data:
            updates.append("category = :category")
            params["category"] = data["category"]
        if "notes" in data:
            updates.append("notes = :notes")
            params["notes"] = data["notes"]
        if "sort_order" in data and data["sort_order"] is not None:
            updates.append("sort_order = CAST(:sort AS smallint)")
            params["sort"] = data["sort_order"]

        set_clause = ", ".join(updates)
        sql = f"UPDATE work_completion_bom SET {set_clause} WHERE bom_id = CAST(:id AS uuid) AND delete_at IS NULL"
        await self.execute(sql, params)

    async def delete_bom_item(self, bom_id: UUID | str) -> None:
        """Soft delete item BoM."""
        sql = """
            UPDATE work_completion_bom
            SET delete_at = NOW(), update_at = NOW()
            WHERE bom_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        await self.execute(sql, {"id": str(bom_id)})

    async def sync_bom_from_work_types(self, completion_id: UUID | str, overwrite_existing: bool = False) -> int:
        """
        Menyalin template material default dari jenis pekerjaan (work_type) seluruh item tugas
        yang terhubung ke order klien ini ke dalam work_completion_bom.
        """
        if overwrite_existing:
            await self.execute(
                """
                UPDATE work_completion_bom
                SET delete_at = NOW(), update_at = NOW()
                WHERE completion_id = CAST(:cid AS uuid) AND delete_at IS NULL
                """,
                {"cid": str(completion_id)},
            )

        sql_fetch_defaults = """
            SELECT DISTINCT ON (COALESCE(dm.material_code, dm.material_name))
                dm.material_code,
                dm.material_name,
                dm.default_qty,
                dm.unit,
                dm.category,
                dm.description,
                dm.sort_order,
                wpi.item_id AS linked_item_id
            FROM work_plan_item wpi
            JOIN work_type_default_materials dm ON dm.work_type_id = wpi.work_type_id
            WHERE wpi.completion_id = CAST(:cid AS uuid)
              AND wpi.delete_at IS NULL
              AND dm.delete_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM work_completion_bom b
                  WHERE b.completion_id = CAST(:cid AS uuid)
                    AND b.delete_at IS NULL
                    AND (
                        (b.material_code IS NOT NULL AND b.material_code = dm.material_code)
                        OR lower(b.material_name) = lower(dm.material_name)
                    )
              )
            ORDER BY COALESCE(dm.material_code, dm.material_name), dm.sort_order
        """
        rows = await self.fetchall(sql_fetch_defaults, {"cid": str(completion_id)})
        count = 0
        for r in rows:
            await self.execute(
                """
                INSERT INTO work_completion_bom (
                    completion_id, work_plan_item_id, material_code, material_name,
                    estimated_qty, actual_qty, unit, category, notes, sort_order
                )
                VALUES (
                    CAST(:cid AS uuid),
                    CAST(:item_id AS uuid),
                    :code,
                    :name,
                    CAST(:qty AS numeric),
                    0.0,
                    :unit,
                    :category,
                    :notes,
                    CAST(:sort AS smallint)
                )
                """,
                {
                    "cid": str(completion_id),
                    "item_id": str(r.linked_item_id) if r.linked_item_id else None,
                    "code": r.material_code,
                    "name": r.material_name,
                    "qty": float(r.default_qty or 1.0),
                    "unit": r.unit or "Unit",
                    "category": r.category,
                    "notes": r.description,
                    "sort": int(r.sort_order or 0),
                },
            )
            count += 1
        return count


# Alias backward compatibility
CRUDWorkCompletion = WorkCompletionRepository
