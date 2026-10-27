"""
app/modules/work_plans/repositories/survey_repository.py
Survei berformat baku (docs/37). Relasi: tugas survei (work_plan_item SURVEY) N─1 work_completion (order laporan);
titik (work_plan_item SURVEY) N─1 tugas (depends_on_item_id); baris titik = work_completion_bom
(work_plan_item_id = titik, category MATERIAL/KEBUTUHAN/KABEL); slot foto = image_requirement work type tugas.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository


class SurveyRepository(BaseRepository):
    """Query tugas survei, titik, baris titik, dan order laporannya."""

    async def task(self, item_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT i.item_id, i.daily_plan_id, i.work_type_id, wt.name AS work_type_name, i.task_phase, i.status,
                   i.depends_on_item_id, i.completion_id, i.approved_by_pm_id, i.target_qty,
                   wpd.work_date, wpd.status AS plan_status, wpd.team_id, wpd.division_id, t.name AS team_name,
                   d.name AS division_name, wc.client_name, wc.project_title, wc.site_address, wc.summary_notes,
                   wc.realization_photos_json AS order_photos, wc.order_status
            FROM work_plan_item i
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id
            JOIN work_type wt ON wt.work_type_id = i.work_type_id
            JOIN division d ON d.division_id = wpd.division_id
            LEFT JOIN team t ON t.team_id = wpd.team_id
            LEFT JOIN work_completion wc ON wc.completion_id = i.completion_id
            WHERE i.item_id = CAST(:id AS uuid) AND i.delete_at IS NULL
            """,
            {"id": str(item_id)},
        )

    async def list_tasks(self, employee_id: str | None, sees_all: bool, state: str | None) -> list[Any]:
        """Tugas survei yang boleh dilihat: semua (admin/OM), divisi yang dipimpin (PM/OM divisi), atau tim sendiri
        (ketua/anggota). Status: DRAFT (belum dikirim), SUBMITTED (menunggu PM), APPROVED."""
        return list(await self.fetchall(
            """
            SELECT i.item_id AS task_id, i.title, i.status, i.approved_by_pm_id, i.update_at, i.completion_id,
                   wpd.daily_plan_id, wpd.work_date, wpd.status AS plan_status, wpd.division_id,
                   d.name AS division_name,
                   t.name AS team_name, wt.name AS work_type_name, wc.client_name, wc.project_title, wc.site_address,
                   (SELECT COUNT(*) FROM work_plan_item p WHERE p.depends_on_item_id = i.item_id
                        AND p.task_phase = 'SURVEY' AND p.delete_at IS NULL) AS point_count,
                   CASE WHEN i.approved_by_pm_id IS NOT NULL THEN 'APPROVED'
                        WHEN i.status = 'DONE' THEN 'SUBMITTED' ELSE 'DRAFT' END AS state
            FROM work_plan_item i
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id AND wpd.delete_at IS NULL
            JOIN division d ON d.division_id = wpd.division_id
            JOIN work_type wt ON wt.work_type_id = i.work_type_id
            LEFT JOIN team t ON t.team_id = wpd.team_id
            JOIN work_completion wc ON wc.completion_id = i.completion_id
            WHERE i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NULL AND i.delete_at IS NULL
              AND (:all OR d.pm_id = CAST(:emp AS uuid) OR d.om_id = CAST(:emp AS uuid)
                   OR (wpd.status NOT IN ('DRAFT', 'SUBMITTED', 'REJECTED')
                       AND (t.leader_employee_id = CAST(:emp AS uuid)
                            OR EXISTS (SELECT 1 FROM member m WHERE m.team_id = t.team_id
                                       AND m.employee_id = CAST(:emp AS uuid) AND m.is_active
                                       AND m.delete_at IS NULL))))
              AND (CAST(:state AS varchar) IS NULL OR CASE WHEN i.approved_by_pm_id IS NOT NULL THEN 'APPROVED'
                        WHEN i.status = 'DONE' THEN 'SUBMITTED' ELSE 'DRAFT' END = CAST(:state AS varchar))
            ORDER BY wpd.work_date DESC, i.update_at DESC
            LIMIT 200
            """,
            {"emp": employee_id, "all": sees_all, "state": state},
        ))

    async def slots(self, work_type_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            "SELECT image_requirement_id AS requirement_id, name, is_mandatory AS mandatory, description AS hint, "
            "CASE WHEN path_image ~ '^[0-9a-f-]{36}$' THEN path_image END AS example_file_id "
            "FROM image_requirement WHERE work_type_id = CAST(:w AS uuid) AND delete_at IS NULL ORDER BY sort_order",
            {"w": str(work_type_id)},
        ))

    async def slot_names(self, work_type_id: UUID | str) -> dict[str, str]:
        """Nama semua slot foto work type — termasuk yang sudah diarsipkan — agar foto lama tetap berlabel."""
        rows = await self.fetchall(
            "SELECT CAST(image_requirement_id AS text) AS id, name FROM image_requirement "
            "WHERE work_type_id = CAST(:w AS uuid)",
            {"w": str(work_type_id)},
        )
        return {r.id: r.name for r in rows}

    async def catalog(self, work_type_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            "SELECT material_name AS name, unit, category, default_qty FROM work_type_default_materials "
            "WHERE work_type_id = CAST(:w AS uuid) AND delete_at IS NULL ORDER BY sort_order, material_name",
            {"w": str(work_type_id)},
        ))

    async def points(self, task_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            "SELECT item_id AS point_id, title AS name, notes, realization_photos_json AS photos, site_lat, "
            "site_lng, update_at, work_type_id, COALESCE(point_status, 'PROPOSED') AS point_status "
            "FROM work_plan_item WHERE depends_on_item_id = CAST(:t AS uuid) "
            "AND task_phase = 'SURVEY' AND delete_at IS NULL ORDER BY create_at",
            {"t": str(task_id)},
        ))

    async def point(self, point_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT p.item_id AS point_id, p.depends_on_item_id AS task_id, p.title AS name, p.notes, "
            "p.realization_photos_json AS photos, p.site_lat, p.site_lng, p.work_type_id FROM work_plan_item p "
            "WHERE p.item_id = CAST(:id AS uuid) AND p.task_phase = 'SURVEY' AND p.depends_on_item_id IS NOT NULL "
            "AND p.delete_at IS NULL",
            {"id": str(point_id)},
        )

    async def lines(self, point_ids: list[str]) -> list[Any]:
        if not point_ids:
            return []
        return list(await self.fetchall(
            "SELECT bom_id, work_plan_item_id AS point_id, COALESCE(category, 'MATERIAL') AS category, "
            "material_name AS name, estimated_qty AS qty, unit, notes FROM work_completion_bom "
            "WHERE work_plan_item_id = ANY(CAST(:ids AS uuid[])) AND delete_at IS NULL ORDER BY sort_order",
            {"ids": point_ids},
        ))

    async def point_types(self, division_id: UUID | str) -> list[Any]:
        """Jenis titik survei (work type SURVEY_POINT) divisi ini — boleh dipakai di semua survei divisinya."""
        return list(await self.fetchall(
            "SELECT work_type_id, name, follow_up_work_type_id FROM work_type "
            "WHERE division_id = CAST(:d AS uuid) AND kind = 'SURVEY_POINT' AND delete_at IS NULL ORDER BY lower(name)",
            {"d": str(division_id)},
        ))

    async def line(self, bom_id: UUID | str) -> Any:
        """Satu baris BoM survei + tugas survei pemiliknya (titik → tugas, atau langsung tugas untuk material umum)."""
        return await self.fetchone(
            """
            SELECT b.bom_id, b.work_plan_item_id, COALESCE(p.depends_on_item_id, p.item_id) AS task_id,
                   b.material_name AS name, b.estimated_qty AS qty, b.unit, COALESCE(b.category, 'MATERIAL') AS category
            FROM work_completion_bom b JOIN work_plan_item p ON p.item_id = b.work_plan_item_id
            WHERE b.bom_id = CAST(:id AS uuid) AND b.delete_at IS NULL AND p.task_phase = 'SURVEY'
            """,
            {"id": str(bom_id)},
        )

    async def insert_line(self, completion_id: UUID | str, item_id: UUID | str, line: dict[str, Any]) -> None:
        await self.execute(
            "INSERT INTO work_completion_bom (completion_id, work_plan_item_id, material_name, estimated_qty, "
            "actual_qty, unit, category, notes, sort_order) VALUES (CAST(:order AS uuid), CAST(:id AS uuid), "
            ":name, :qty, 0, :unit, :category, :notes, "
            "(SELECT COALESCE(MAX(sort_order), 0) + 1 FROM work_completion_bom "
            "WHERE work_plan_item_id = CAST(:id AS uuid)))",
            {**line, "order": str(completion_id), "id": str(item_id)},
        )

    async def update_line(self, bom_id: UUID | str, line: dict[str, Any]) -> None:
        await self.execute(
            "UPDATE work_completion_bom SET material_name = :name, estimated_qty = :qty, unit = :unit, "
            "update_at = now() WHERE bom_id = CAST(:id AS uuid)",
            {**line, "id": str(bom_id)},
        )

    async def delete_line(self, bom_id: UUID | str) -> None:
        await self.execute("DELETE FROM work_completion_bom WHERE bom_id = CAST(:id AS uuid)", {"id": str(bom_id)})

    async def add_catalog(self, work_type_id: UUID | str, name: str, unit: str) -> bool:
        """Material di luar katalog → katalog jenis titik (False bila namanya sudah ada)."""
        added = await self.scalar(
            """
            INSERT INTO work_type_default_materials (work_type_id, material_name, default_qty, unit, category,
                                                     sort_order)
            SELECT CAST(:w AS uuid), CAST(:name AS varchar), 1, CAST(:unit AS varchar), 'MATERIAL',
                   (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM work_type_default_materials
                    WHERE work_type_id = CAST(:w AS uuid))
            WHERE NOT EXISTS (SELECT 1 FROM work_type_default_materials WHERE work_type_id = CAST(:w AS uuid)
                              AND lower(material_name) = lower(CAST(:name AS varchar)) AND delete_at IS NULL)
            RETURNING 1
            """,
            {"w": str(work_type_id), "name": name, "unit": unit},
        )
        return bool(added)

    async def review_note(self, task_id: UUID | str) -> str | None:
        note: str | None = await self.scalar(
            "SELECT changed_diff->>'note' FROM app_activity_logs WHERE entity_table = 'work_plan_item' "
            "AND entity_id = CAST(:id AS uuid) AND action IN ('SURVEY_RETURNED', 'SURVEY_APPROVED') "
            "ORDER BY created_at DESC LIMIT 1",
            {"id": str(task_id)},
        )
        return note

    async def existing_files(self, file_ids: list[str]) -> int:
        return int(await self.scalar(
            "SELECT COUNT(*) FROM file_object WHERE id = ANY(CAST(:ids AS uuid[]))", {"ids": list(set(file_ids))}
        ) or 0)

    # ── Tulis ─────────────────────────────────────────────────────────────────
    async def insert_point(self, task: Any, data: dict[str, Any]) -> UUID:
        point_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                                        completion_id, depends_on_item_id, target_qty, completed_qty,
                                        progress_percent, status, location_name, site_lat, site_lng, notes,
                                        realization_photos_json, point_status)
            VALUES (CAST(:daily AS uuid), CAST(:wt AS uuid), :name, 'SURVEY', FALSE, CAST(:order AS uuid),
                    CAST(:task AS uuid), 1, 0, 0, 'IN_PROGRESS', :name, CAST(:lat AS numeric), CAST(:lng AS numeric),
                    :notes, CAST(:photos AS jsonb), :status)
            RETURNING item_id
            """,
            {"daily": str(task.daily_plan_id), "order": str(task.completion_id), "task": str(task.item_id), **data},
        )
        return point_id

    async def update_point(self, point_id: UUID | str, data: dict[str, Any]) -> None:
        await self.execute(
            "UPDATE work_plan_item SET title = :name, location_name = :name, notes = :notes, "
            "work_type_id = CAST(:wt AS uuid), point_status = :status, "
            "realization_photos_json = CAST(:photos AS jsonb), site_lat = CAST(:lat AS numeric), "
            "site_lng = CAST(:lng AS numeric), update_at = now() WHERE item_id = CAST(:id AS uuid)",
            {**data, "id": str(point_id)},
        )

    async def replace_lines(self, completion_id: UUID | str, point_id: UUID | str, lines: list[dict[str, Any]]) -> None:
        params = {"id": str(point_id)}
        await self.execute("DELETE FROM work_completion_bom WHERE work_plan_item_id = CAST(:id AS uuid)", params)
        for n, line in enumerate(lines, start=1):
            await self.execute(
                "INSERT INTO work_completion_bom (completion_id, work_plan_item_id, material_name, estimated_qty, "
                "actual_qty, unit, category, notes, sort_order) VALUES (CAST(:order AS uuid), CAST(:id AS uuid), "
                ":name, :qty, 0, :unit, :category, :notes, :n)",
                {**params, **line, "order": str(completion_id), "n": n},
            )

    async def archive_point(self, point_id: UUID | str) -> None:
        params = {"id": str(point_id)}
        await self.execute("DELETE FROM work_completion_bom WHERE work_plan_item_id = CAST(:id AS uuid)", params)
        await self.execute(
            "UPDATE work_plan_item SET delete_at = now(), update_at = now() WHERE item_id = CAST(:id AS uuid)", params)

    async def save_report(self, completion_id: UUID | str, fields: dict[str, Any]) -> None:
        await self.execute(
            """
            UPDATE work_completion SET summary_notes = COALESCE(:narrative, summary_notes),
                   project_title = COALESCE(:purpose, project_title), site_address = COALESCE(:location, site_address),
                   update_at = now()
            WHERE completion_id = CAST(:id AS uuid)
            """,
            {**fields, "id": str(completion_id)},
        )

    async def set_task_state(self, task_id: UUID | str, *, done: bool, approver: str | None) -> None:
        """Kirim (done) / kembalikan (tidak done) / setujui (approver). Titik ikut status tugas."""
        params = {"id": str(task_id), "done": done, "pm": approver}
        await self.execute(
            """
            UPDATE work_plan_item SET
                status = CASE WHEN :done THEN 'DONE' ELSE 'IN_PROGRESS' END,
                completed_qty = CASE WHEN :done THEN target_qty ELSE 0 END,
                progress_percent = CASE WHEN :done THEN 100 ELSE 0 END,
                approved_by_pm_id = CAST(:pm AS uuid), update_at = now()
            WHERE item_id = CAST(:id AS uuid) OR (depends_on_item_id = CAST(:id AS uuid) AND task_phase = 'SURVEY'
                                                AND delete_at IS NULL)
            """,
            params,
        )

    async def log(self, user_id: str, role: str, task_id: UUID | str, action: str, diff: dict[str, Any]) -> None:
        await self.execute(
            """
            INSERT INTO app_activity_logs (actor_user_id, actor_role, platform, action, entity_table, entity_id,
                                           changed_diff)
            VALUES (CAST(:uid AS uuid), :role, CAST(:platform AS client_platform_enum), :action, 'work_plan_item',
                    CAST(:id AS uuid),
                    CAST(:diff AS jsonb))
            """,
            {"uid": user_id, "role": role[:30], "action": action, "id": str(task_id),
             "platform": "android_flutter" if role in ("TEAM_LEADER", "EMPLOYEE") else "web_react",
             "diff": json.dumps(diff, default=str)},
        )

    async def plan_target(self, daily_plan_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT daily_plan_id, work_date, team_id, division_id, status FROM work_plan_daily "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        )

    async def set_point_location(self, point_id: UUID | str, lat: Any, lng: Any) -> None:
        await self.execute(
            "UPDATE work_plan_item SET site_lat = :lat, site_lng = :lng, update_at = now() "
            "WHERE item_id = CAST(:id AS uuid)", {"id": str(point_id), "lat": lat, "lng": lng})

    async def team_day(self, team_id: UUID | str, work_date: Any) -> Any:
        return await self.fetchone(
            "SELECT daily_plan_id, work_date, team_id, division_id, status FROM work_plan_daily "
            "WHERE team_id = CAST(:t AS uuid) AND work_date = :d AND delete_at IS NULL",
            {"t": str(team_id), "d": work_date},
        )

    async def draft_day(
        self,
        source_daily_id: UUID | str,
        work_date: Any,
        author: str | None,
        team_id: UUID | str | None = None,
    ) -> UUID:
        """Jadwal DRAFT baru untuk tim survei di tanggal lanjutan (lokasi, radius, jam disalin dari hari survei)."""
        new_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_daily (division_id, team_id, project_id, work_date, site_name, site_lat, site_lng,
                                         attendance_radius_m, clock_in_time, clock_out_time, status, created_by_id)
            SELECT division_id, COALESCE(CAST(:tid AS uuid), team_id), project_id, :d,
                   site_name, site_lat, site_lng, attendance_radius_m,
                   clock_in_time, clock_out_time, 'DRAFT', COALESCE(CAST(:by AS uuid), created_by_id)
            FROM work_plan_daily WHERE daily_plan_id = CAST(:id AS uuid)
            RETURNING daily_plan_id
            """,
            {"id": str(source_daily_id), "d": work_date, "by": author, "tid": str(team_id) if team_id else None},
        )
        return new_id

    async def work_type_division(self, work_type_id: UUID | str) -> str | None:
        div = await self.scalar(
            "SELECT CAST(division_id AS text) FROM work_type "
            "WHERE work_type_id = CAST(:w AS uuid) AND delete_at IS NULL "
            "AND kind IN ('WORK', 'INSTALLATION', 'MAINTENANCE', 'REPLACEMENT', 'PREPARATION', 'SURVEY_POINT')",
            {"w": str(work_type_id)},
        )
        return str(div) if div else None

    async def insert_follow_up(self, daily_plan_id: UUID | str, completion_id: UUID | str, work_type_id: UUID | str,
                               phase: str, point: Any, notes: str | None) -> UUID:
        item_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                                        completion_id, depends_on_item_id, target_qty, completed_qty,
                                        progress_percent, status, location_name, site_lat, site_lng, notes)
            VALUES (CAST(:daily AS uuid), CAST(:wt AS uuid), :title, :phase, :main, CAST(:order AS uuid),
                    CAST(:point AS uuid), 1, 0, 0, 'TODO', :loc, CAST(:lat AS numeric), CAST(:lng AS numeric), :notes)
            RETURNING item_id
            """,
            {"daily": str(daily_plan_id), "wt": str(work_type_id), "phase": phase,
             "title": f"{'Persiapan' if phase == 'PREPARATION' else 'Pekerjaan'} — {point.name}"[:200],
             "main": phase in ("INSTALLATION", "REPLACEMENT", "MAINTENANCE"), "order": str(completion_id),
             "point": str(point.point_id), "loc": point.name[:150], "lat": point.site_lat, "lng": point.site_lng,
             "notes": notes},
        )
        return item_id

    async def create_task(self, data: dict[str, Any]) -> UUID | None:
        """Buat tugas survei baru (work_plan_item SURVEY) dari order completion/revisi jika konteks tersedia."""
        cid = data.get("completion_id")
        if not cid:
            return None
        order = await self.fetchone(
            "SELECT daily_plan_id, division_id FROM work_completion WHERE completion_id = CAST(:cid AS uuid)",
            {"cid": str(cid)},
        )
        if not order:
            return None
        daily_plan_id = order.daily_plan_id
        division_id = order.division_id or data.get("division_id")
        if not daily_plan_id or not division_id:
            return None

        wt_id = await self.scalar(
            """
            SELECT work_type_id FROM work_type
            WHERE division_id = CAST(:div AS uuid) AND delete_at IS NULL
            ORDER BY (kind = 'SURVEY_TASK' OR strpos(lower(name), 'survei') > 0) DESC, create_at ASC
            LIMIT 1
            """,
            {"div": str(division_id)},
        )
        if not wt_id:
            return None

        title = (data.get("title") or "Survei Revisi Pekerjaan")[:200]
        notes = data.get("description")

        item_id = await self.scalar(
            """
            INSERT INTO work_plan_item (
                daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                completion_id, target_qty, completed_qty, progress_percent, status,
                notes, realization_photos_json
            ) VALUES (
                CAST(:daily AS uuid), CAST(:wt AS uuid), :title, 'SURVEY', FALSE,
                CAST(:order AS uuid), 1, 0, 0, 'TODO',
                :notes, '[]'::jsonb
            )
            RETURNING item_id
            """,
            {
                "daily": str(daily_plan_id),
                "wt": str(wt_id),
                "title": title,
                "order": str(cid),
                "notes": notes,
            },
        )
        return UUID(str(item_id)) if item_id else None
