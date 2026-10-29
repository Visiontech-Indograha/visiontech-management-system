"""
app/modules/exports/repositories/export_repository.py
Data dokumen resmi (Milestone 8, docs/35 §8) + registri `document_template_export`.

Relasi: work_completion 1─N work_plan_item (completion_id) N─1 work_plan_daily N─1 team 1─N member;
work_completion 1─N work_completion_bom (opsional per item); document_template_export N─1 work_completion /
work_plan_daily / employee (generated_by_id). Foto realisasi = file_object (id di realization_photos_json).
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_EXPORT_COLS = """
    x.export_id, x.source_type, x.completion_id, x.daily_plan_id, x.period_start_date, x.period_end_date,
    x.template_type, x.export_format::text AS export_format, x.file_output_url, x.generated_by_id,
    e.full_name AS generated_by_name, x.create_at
"""


class ExportRepository(BaseRepository):
    """Query bahan dokumen & registri ekspor."""

    async def employee_name(self, employee_id: UUID | str) -> str | None:
        val: str | None = await self.scalar(
            "SELECT full_name FROM employee WHERE employee_id = CAST(:id AS uuid)", {"id": str(employee_id)})
        return val

    # ── Bahan dokumen order ───────────────────────────────────────────────────
    async def completion_items(self, completion_id: UUID | str) -> list[Any]:
        """Item (titik) order, urut tanggal & jam; termasuk nama penugasan dan foto realisasinya."""
        return await self._items("i.completion_id = CAST(:id AS uuid)", {"id": str(completion_id)})

    async def team_week_items(self, team_id: UUID | str, start: date, end: date) -> list[Any]:
        """Semua pekerjaan satu tim dalam rentang tanggal (laporan mingguan tim)."""
        return await self._items(
            "d.team_id = CAST(:team AS uuid) AND d.work_date BETWEEN :start AND :end "
            "AND d.status IN ('APPROVED', 'ONGOING', 'COMPLETED')",
            {"team": str(team_id), "start": start, "end": end},
        )

    async def daily_items(self, daily_plan_id: UUID | str) -> list[Any]:
        """Item satu jadwal harian (laporan harian cetak)."""
        return await self._items("d.daily_plan_id = CAST(:d AS uuid)", {"d": str(daily_plan_id)})

    async def daily_header(self, daily_plan_id: UUID | str) -> Any:
        """Jadwal + tim + divisi + ketua + laporan harian ketua (bila sudah dikirim)."""
        return await self.fetchone(
            """
            SELECT d.daily_plan_id, d.team_id, d.work_date, d.site_name, d.status::text AS status,
                   t.name AS team_name, dv.name AS division_name,
                   COALESCE(le.full_name, '-') AS leader_name,
                   r.summary, r.obstacles, r.submitted_at AS report_submitted_at
            FROM work_plan_daily d
            JOIN team t ON t.team_id = d.team_id
            JOIN division dv ON dv.division_id = t.division_id
            LEFT JOIN employee le ON le.employee_id = t.leader_employee_id
            LEFT JOIN work_plan_daily_report r ON r.daily_plan_id = d.daily_plan_id AND r.delete_at IS NULL
            WHERE d.daily_plan_id = CAST(:d AS uuid) AND d.delete_at IS NULL
            """,
            {"d": str(daily_plan_id)},
        )

    async def team_info(self, team_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT t.team_id, t.name, t.division_id, t.leader_employee_id, d.name AS division_name "
            "FROM team t JOIN division d ON d.division_id = t.division_id "
            "WHERE t.team_id = CAST(:t AS uuid) AND t.delete_at IS NULL",
            {"t": str(team_id)},
        )

    async def team_logo_keys(self, team_ids: list[str]) -> dict[str, str]:
        """team_id → storage_key logo tim (hanya tim yang punya logo)."""
        if not team_ids:
            return {}
        rows = await self.fetchall(
            """
            SELECT CAST(t.team_id AS text) AS team_id, fo.storage_key
            FROM team t JOIN file_object fo ON fo.id = t.logo_file_id
            WHERE t.team_id = ANY(CAST(:ids AS uuid[])) AND t.delete_at IS NULL
            """,
            {"ids": team_ids},
        )
        return {str(r.team_id): r.storage_key for r in rows}

    async def is_team_member(self, team_id: UUID | str, employee_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM team t WHERE t.team_id = CAST(:t AS uuid) "
            "AND t.leader_employee_id = CAST(:e AS uuid)) OR EXISTS (SELECT 1 FROM member m "
            "WHERE m.team_id = CAST(:t AS uuid) AND m.employee_id = CAST(:e AS uuid) AND m.delete_at IS NULL)",
            {"t": str(team_id), "e": str(employee_id)},
        ))

    async def _items(self, where: str, params: dict[str, Any]) -> list[Any]:
        return list(await self.fetchall(
            f"""
            SELECT i.item_id, i.title, i.task_phase, i.status, i.location_name,
                   i.site_lat::float AS site_lat, i.site_lng::float AS site_lng,
                   i.target_qty::float AS target_qty, i.completed_qty::float AS completed_qty,
                   i.progress_percent::float AS progress_percent, i.notes, i.delay_reason,
                   i.realization_photos_json AS photos, i.is_main_deliverable,
                   i.start_time, i.end_time, wt.name AS work_type_name,
                   d.daily_plan_id, d.work_date, d.site_name, t.team_id, t.name AS team_name,
                   COALESCE((SELECT string_agg(e.full_name, ', ' ORDER BY e.full_name)
                             FROM employee e
                             WHERE i.assigned_employee_ids ? e.employee_id::text), '') AS assignees
            FROM work_plan_item i
            JOIN work_plan_daily d ON d.daily_plan_id = i.daily_plan_id AND d.delete_at IS NULL
            JOIN team t ON t.team_id = d.team_id
            JOIN work_type wt ON wt.work_type_id = i.work_type_id
            WHERE {where} AND i.delete_at IS NULL
            ORDER BY d.work_date, i.start_time NULLS LAST, i.title
            """,
            params,
        ))

    async def team_roster(self, team_ids: list[str]) -> list[Any]:
        """Ketua + anggota aktif tim yang mengerjakan order."""
        if not team_ids:
            return []
        return list(await self.fetchall(
            """
            SELECT t.team_id, t.name AS team_name, e.full_name, e.employee_no, (e.employee_id = t.leader_employee_id)
                   AS is_leader
            FROM team t
            JOIN employee e ON e.employee_id = t.leader_employee_id
                 OR e.employee_id IN (SELECT m.employee_id FROM member m WHERE m.team_id = t.team_id
                                      AND m.is_active AND m.delete_at IS NULL)
            WHERE t.team_id = ANY(CAST(:ids AS uuid[])) AND e.delete_at IS NULL
            ORDER BY t.name, is_leader DESC, e.full_name
            """,
            {"ids": team_ids},
        ))

    async def requirement_names(self, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        rows = await self.fetchall(
            "SELECT image_requirement_id::text AS id, name FROM image_requirement "
            "WHERE image_requirement_id = ANY(CAST(:ids AS uuid[]))",
            {"ids": ids},
        )
        return {r.id: r.name for r in rows}

    async def image_keys(self, file_ids: list[str]) -> dict[str, str]:
        """file_object id → storage_key, hanya gambar."""
        if not file_ids:
            return {}
        rows = await self.fetchall(
            "SELECT id::text AS id, storage_key FROM file_object "
            "WHERE id = ANY(CAST(:ids AS uuid[])) AND mime_type LIKE 'image/%'",
            {"ids": file_ids},
        )
        return {r.id: r.storage_key for r in rows}

    # ── Bahan rekap periodik (divisi × rentang tanggal) ──────────────────────
    async def division_name(self, division_id: UUID | str) -> str | None:
        name: str | None = await self.scalar(
            "SELECT name FROM division WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(division_id)},
        )
        return name

    async def periodic_days(self, division_id: UUID | str, start: date, end: date) -> list[Any]:
        """Jadwal harian divisi pada rentang + ringkasan itemnya."""
        return list(await self.fetchall(
            """
            SELECT d.daily_plan_id, d.work_date, d.site_name, d.status, t.name AS team_name,
                   COUNT(i.item_id)::int AS items,
                   COUNT(i.item_id) FILTER (WHERE i.status = 'DONE')::int AS items_done,
                   COUNT(i.item_id) FILTER (WHERE i.status IN ('PENDING_ROLLOVER', 'SHIFTED_DAY'))::int
                       AS items_shifted,
                   COALESCE(ROUND(AVG(i.progress_percent), 1), 0)::float AS avg_progress,
                   COALESCE(string_agg(i.title, '; ' ORDER BY i.start_time NULLS LAST, i.title), '') AS titles
            FROM work_plan_daily d
            JOIN team t ON t.team_id = d.team_id
            LEFT JOIN work_plan_item i ON i.daily_plan_id = d.daily_plan_id AND i.delete_at IS NULL
            WHERE d.division_id = CAST(:div AS uuid) AND d.delete_at IS NULL
              AND d.work_date BETWEEN :start AND :end
            GROUP BY d.daily_plan_id, d.work_date, d.site_name, d.status, t.name
            ORDER BY d.work_date, t.name
            """,
            {"div": str(division_id), "start": start, "end": end},
        ))

    async def periodic_boq(self, division_id: UUID | str, start: date, end: date) -> list[Any]:
        """BoQ material per order yang punya item dalam rentang (dijumlah per material)."""
        return list(await self.fetchall(
            """
            SELECT wc.order_number, wc.client_name, wc.project_title, b.material_code, b.material_name, b.unit,
                   SUM(b.estimated_qty)::float AS estimated_qty, SUM(b.actual_qty)::float AS actual_qty
            FROM work_completion wc
            JOIN work_completion_bom b ON b.completion_id = wc.completion_id AND b.delete_at IS NULL
                 AND COALESCE(b.category, 'MATERIAL') NOT IN ('KEBUTUHAN', 'KABEL')
            WHERE wc.division_id = CAST(:div AS uuid) AND wc.delete_at IS NULL
              AND EXISTS (SELECT 1 FROM work_plan_item i
                          JOIN work_plan_daily d ON d.daily_plan_id = i.daily_plan_id AND d.delete_at IS NULL
                          WHERE i.completion_id = wc.completion_id AND i.delete_at IS NULL
                            AND d.work_date BETWEEN :start AND :end)
            GROUP BY wc.order_number, wc.client_name, wc.project_title, b.material_code, b.material_name, b.unit
            ORDER BY wc.client_name, wc.project_title, b.material_name
            """,
            {"div": str(division_id), "start": start, "end": end},
        ))

    async def periodic_meal(self, division_id: UUID | str, start: date, end: date) -> list[Any]:
        """Uang makan karyawan divisi: hanya absensi sah (sama dengan rekap absensi M7)."""
        return list(await self.fetchall(
            """
            SELECT e.employee_no, e.full_name,
                   COUNT(*) FILTER (WHERE ok AND a.city_zone_status = 'DALAM_KOTA')::int AS in_city_days,
                   COUNT(*) FILTER (WHERE ok AND a.city_zone_status = 'LUAR_KOTA')::int AS out_city_days,
                   COALESCE(SUM(a.meal_allowance_amount) FILTER (WHERE ok), 0)::float AS total_amount,
                   COUNT(*) FILTER (WHERE a.om_approval_status = 'PENDING_OM')::int AS pending_days
            FROM attendance a
            CROSS JOIN LATERAL (SELECT a.om_approval_status IN ('AUTO_VALID', 'APPROVED_BY_OM') AS ok) v
            JOIN employee e ON e.employee_id = a.employee_id
            WHERE a.delete_at IS NULL AND e.division_id = CAST(:div AS uuid)
              AND a.attendance_date BETWEEN :start AND :end
            GROUP BY e.employee_no, e.full_name
            ORDER BY e.full_name
            """,
            {"div": str(division_id), "start": start, "end": end},
        ))

    # ── Registri document_template_export ────────────────────────────────────
    async def insert_export(self, *, source_type: str, completion_id: UUID | str | None, period_start: date | None,
                            period_end: date | None, template_type: str, master_template: str, export_format: str,
                            storage_key: str, generated_by: UUID | str,
                            daily_plan_id: UUID | str | None = None) -> Any:
        return await self.fetchone(
            f"""
            WITH x AS (
                INSERT INTO document_template_export (
                    source_type, completion_id, period_start_date, period_end_date, template_type,
                    master_template_path, export_format, file_output_url, generated_by_id, daily_plan_id
                ) VALUES (
                    :source, CAST(:cid AS uuid), :pstart, :pend, :tpl, :master,
                    CAST(:fmt AS export_format_enum), :key, CAST(:by AS uuid), CAST(:daily AS uuid)
                ) RETURNING export_id, source_type, completion_id, daily_plan_id, period_start_date, period_end_date,
                            template_type, export_format, file_output_url, generated_by_id, create_at
            )
            SELECT {_EXPORT_COLS} FROM x JOIN employee e ON e.employee_id = x.generated_by_id
            """,
            {"source": source_type, "cid": str(completion_id) if completion_id else None, "pstart": period_start,
             "pend": period_end, "tpl": template_type, "master": master_template, "fmt": export_format,
             "key": storage_key, "by": str(generated_by),
             "daily": str(daily_plan_id) if daily_plan_id else None},
        )

    async def list_exports(self, *, completion_id: UUID | str | None = None,
                           generated_by: UUID | str | None = None, limit: int = 50) -> list[Any]:
        """Riwayat ekspor satu order, atau rekap periodik buatan seseorang (None = semua periodik)."""
        return list(await self.fetchall(
            f"""
            SELECT {_EXPORT_COLS}
            FROM document_template_export x
            JOIN employee e ON e.employee_id = x.generated_by_id
            WHERE x.delete_at IS NULL
              AND (CASE WHEN CAST(:cid AS uuid) IS NOT NULL THEN x.completion_id = CAST(:cid AS uuid)
                        ELSE x.source_type = 'WORK_PLAN_PERIODIC'
                             AND (CAST(:by AS uuid) IS NULL OR x.generated_by_id = CAST(:by AS uuid)) END)
            ORDER BY x.create_at DESC
            LIMIT :limit
            """,
            {"cid": str(completion_id) if completion_id else None,
             "by": str(generated_by) if generated_by else None, "limit": limit},
        ))

    async def get_export(self, export_id: UUID | str) -> Any:
        return await self.fetchone(
            f"""
            SELECT {_EXPORT_COLS}
            FROM document_template_export x
            JOIN employee e ON e.employee_id = x.generated_by_id
            WHERE x.export_id = CAST(:id AS uuid) AND x.delete_at IS NULL
            """,
            {"id": str(export_id)},
        )


def photo_refs(raw: Any) -> list[dict[str, str | None]]:
    """realization_photos_json → [{file_id, requirement_id}]. Bentuk lama (larik id/path) tetap terbaca."""
    data = json.loads(raw) if isinstance(raw, str) else (raw or [])
    refs: list[dict[str, str | None]] = []
    for p in data if isinstance(data, list) else []:
        if isinstance(p, dict) and p.get("file_id"):
            refs.append({"file_id": str(p["file_id"]), "requirement_id": p.get("requirement_id")})
        elif isinstance(p, str):
            refs.append({"file_id": p, "requirement_id": None})
    return refs
