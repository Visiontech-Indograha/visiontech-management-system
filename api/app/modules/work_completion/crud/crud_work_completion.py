"""
app/modules/work_completion/crud/crud_work_completion.py

Akses data database untuk entitas Work Completion (Order Klien) Master V3.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.crud.base import CRUDBase


class CRUDWorkCompletion(CRUDBase):
    """CRUD untuk pengelolaan Order Proyek Klien."""

    async def list_completions(
        self,
        *,
        division_id: UUID | str | None = None,
        status: str | None = None,
        search: str | None = None,
        pm_id: UUID | str | None = None,
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
            filters.append("wc.pm_id = CAST(:pm_id AS uuid)")
            params["pm_id"] = str(pm_id)

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
                    WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL
                ), 0) AS completed_target_unit,
                wc.unit_measure,
                wc.order_status,
                wc.priority_level,
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
        return [dict(r) for r in rows]

    async def count_completions(
        self,
        *,
        division_id: UUID | str | None = None,
        status: str | None = None,
        search: str | None = None,
        pm_id: UUID | str | None = None,
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
            filters.append("wc.pm_id = CAST(:pm_id AS uuid)")
            params["pm_id"] = str(pm_id)

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
                    WHERE wpi.completion_id = wc.completion_id AND wpi.delete_at IS NULL
                ), 0) AS completed_target_unit,
                wc.unit_measure,
                wc.order_status,
                wc.priority_level,
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
            WHERE wc.completion_id = CAST(:id AS uuid) AND wc.delete_at IS NULL
        """
        row = await self.fetchone(sql, {"id": str(completion_id)})
        return dict(row) if row else None

    async def create_completion(self, data: dict[str, Any]) -> str:
        """Membuat order proyek baru."""
        sql = """
            INSERT INTO work_completion (
                division_id, pm_id, client_name, project_title, order_number,
                total_target_unit, unit_measure, order_status, priority_level,
                site_address, site_lat, site_lng, summary_notes, realization_photos_json
            ) VALUES (
                CAST(:division_id AS uuid),
                CAST(:pm_id AS uuid),
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
                "division_id": str(data["division_id"]),
                "pm_id": str(data["pm_id"]) if data.get("pm_id") else None,
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
                "summary_notes": data.get("summary_notes"),
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
            SET order_status = :status,
                summary_notes = CASE
                    WHEN :notes IS NOT NULL
                    THEN COALESCE(summary_notes, '') || E'\n[Status ' || :status || ']: ' || :notes
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
        role: str,
        signature_path: str,
        summary_notes: str | None,
        obstacles: str | None,
        photos: list[str],
        signature_hash: str,
    ) -> None:
        """Membubuhkan tanda tangan digital leader atau PM."""
        if role == "TEAM_LEADER":
            sql = """
                UPDATE work_completion
                SET leader_signer_id = CAST(:signer_id AS uuid),
                    leader_signature_path = :sig_path,
                    leader_signed_at = NOW(),
                    summary_notes = COALESCE(:summary_notes, summary_notes),
                    obstacles = COALESCE(:obstacles, obstacles),
                    realization_photos_json = CAST(:photos AS jsonb),
                    signature_hash = :sig_hash,
                    update_at = NOW()
                WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL
            """
        else:
            sql = """
                UPDATE work_completion
                SET pm_signer_id = CAST(:signer_id AS uuid),
                    pm_signature_path = :sig_path,
                    pm_signed_at = NOW(),
                    order_status = 'COMPLETED',
                    signature_hash = :sig_hash,
                    update_at = NOW()
                WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL
            """
        await self.execute(
            sql,
            {
                "id": str(completion_id),
                "signer_id": str(signer_id),
                "sig_path": signature_path,
                "summary_notes": summary_notes,
                "obstacles": obstacles,
                "photos": json.dumps(photos),
                "sig_hash": signature_hash,
            },
        )
