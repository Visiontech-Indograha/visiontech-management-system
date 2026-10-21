"""
app/modules/work_plans/repositories/plan_item_repository.py
Item pekerjaan per titik (Master Schema V2): work_plan_item N─1 work_plan_daily, N─1 work_type, N─1 work_completion
(order), N─1 work_plan_item (depends_on = prasyarat; origin = item asal rollover), N─1 work_plan_daily (shifted_to).
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT i.item_id, i.daily_plan_id, wpd.work_date, i.work_type_id, wt.name AS work_type_name, i.title,
           i.task_phase, i.is_main_deliverable, i.completion_id, wc.project_title AS order_title,
           i.depends_on_item_id, dep.title AS depends_on_title, i.target_qty, i.completed_qty, i.progress_percent,
           i.status, i.rollover_approval_status::text AS rollover_approval_status, i.approved_by_pm_id,
           i.origin_item_id, i.shifted_to_daily_id, i.delay_reason, i.notes, i.start_time, i.end_time,
           i.location_name, i.site_lat, i.site_lng, COALESCE(i.assigned_employee_ids, '[]'::jsonb)
               AS assigned_employee_ids, i.realization_photos_json, i.update_at
    FROM work_plan_item i
    JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id
    JOIN work_type wt ON wt.work_type_id = i.work_type_id
    LEFT JOIN work_completion wc ON wc.completion_id = i.completion_id
    LEFT JOIN work_plan_item dep ON dep.item_id = i.depends_on_item_id
"""

_FIELDS = ("work_type_id", "title", "task_phase", "is_main_deliverable", "completion_id", "depends_on_item_id",
           "target_qty", "start_time", "end_time", "location_name", "site_lat", "site_lng", "notes")


def _params(fields: dict[str, Any]) -> dict[str, Any]:
    out = {k: (str(v) if isinstance(v, UUID) else v) for k, v in fields.items()}
    if "assigned_employee_ids" in fields:
        ids = fields["assigned_employee_ids"]
        out["assigned_employee_ids"] = None if ids is None else json.dumps([str(e) for e in ids])
    return out


class PlanItemRepository(BaseRepository):
    """Query work_plan_item & rujukannya."""

    async def get(self, item_id: UUID | str) -> Any:
        return await self.fetchone(
            _SELECT + " WHERE i.item_id = CAST(:id AS uuid) AND i.delete_at IS NULL", {"id": str(item_id)}
        )

    async def lock(self, item_id: UUID | str) -> Any:
        """Kunci baris item (FOR UPDATE) — dua keputusan rollover bersamaan tidak lolos."""
        return await self.fetchone(
            "SELECT item_id, daily_plan_id, status, rollover_approval_status::text AS rollover_approval_status, "
            "target_qty, completed_qty FROM work_plan_item WHERE item_id = CAST(:id AS uuid) AND delete_at IS NULL "
            "FOR UPDATE",
            {"id": str(item_id)},
        )

    async def of_daily(self, daily_plan_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            _SELECT + " WHERE i.daily_plan_id = CAST(:d AS uuid) AND i.delete_at IS NULL "
            "ORDER BY i.start_time NULLS LAST, i.create_at",
            {"d": str(daily_plan_id)},
        ))

    async def work_type_division(self, work_type_id: UUID | str) -> str | None:
        val = await self.scalar(
            "SELECT CAST(division_id AS text) FROM work_type WHERE work_type_id = CAST(:id AS uuid) "
            "AND delete_at IS NULL",
            {"id": str(work_type_id)},
        )
        return str(val) if val else None

    async def order_division(self, completion_id: UUID | str) -> Any:
        """(division_id, terbuka?) order klien."""
        return await self.fetchone(
            "SELECT CAST(division_id AS text) AS division_id, order_status NOT IN ('COMPLETED', 'CANCELLED') AS open "
            "FROM work_completion WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(completion_id)},
        )

    async def prerequisite(self, item_id: UUID | str) -> Any:
        """Item prasyarat: jadwal, tanggal, tim, order, statusnya."""
        return await self.fetchone(
            "SELECT i.item_id, i.status, i.completion_id, wpd.work_date, wpd.team_id, wpd.division_id "
            "FROM work_plan_item i JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id "
            "WHERE i.item_id = CAST(:id AS uuid) AND i.delete_at IS NULL AND wpd.delete_at IS NULL",
            {"id": str(item_id)},
        )

    async def team_members(self, team_id: UUID | str) -> set[str]:
        rows = await self.fetchall(
            "SELECT CAST(employee_id AS text) AS id FROM member WHERE team_id = CAST(:t AS uuid) "
            "AND is_active AND delete_at IS NULL",
            {"t": str(team_id)},
        )
        return {r.id for r in rows}

    async def dependents(self, item_id: UUID | str) -> int:
        return int(await self.scalar(
            "SELECT COUNT(*) FROM work_plan_item WHERE depends_on_item_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(item_id)},
        ) or 0)

    async def insert(self, daily_plan_id: UUID | str, fields: dict[str, Any]) -> UUID:
        p = _params(fields)
        item_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                                        completion_id, depends_on_item_id, target_qty, completed_qty, progress_percent,
                                        status, start_time, end_time, location_name, site_lat, site_lng,
                                        assigned_employee_ids, notes, origin_item_id)
            VALUES (CAST(:daily AS uuid), CAST(:work_type_id AS uuid), :title, :task_phase, :is_main_deliverable,
                    CAST(:completion_id AS uuid), CAST(:depends_on_item_id AS uuid), :target_qty, 0, 0, 'TODO',
                    CAST(:start_time AS time), CAST(:end_time AS time), :location_name,
                    CAST(:site_lat AS numeric), CAST(:site_lng AS numeric), CAST(:assigned_employee_ids AS jsonb),
                    :notes, CAST(:origin_item_id AS uuid))
            RETURNING item_id
            """,
            {"daily": str(daily_plan_id), "origin_item_id": None, **p},
        )
        return item_id

    async def update(self, item_id: UUID | str, fields: dict[str, Any]) -> None:
        """Ubah sebagian; kolom yang tidak dikirim tidak disentuh (`_sent` = nama kolom yang dikirim)."""
        sent = [k for k in (*_FIELDS, "assigned_employee_ids") if k in fields]
        if not sent:
            return
        casts = {"work_type_id": "uuid", "completion_id": "uuid", "depends_on_item_id": "uuid", "start_time": "time",
                 "end_time": "time", "site_lat": "numeric", "site_lng": "numeric", "assigned_employee_ids": "jsonb",
                 "target_qty": "numeric"}
        sets = ", ".join(f"{k} = CAST(:{k} AS {casts[k]})" if k in casts else f"{k} = :{k}" for k in sent)
        await self.execute(
            f"UPDATE work_plan_item SET {sets}, update_at = now() WHERE item_id = CAST(:id AS uuid)",
            {**_params({k: fields[k] for k in sent}), "id": str(item_id)},
        )

    async def set_progress(self, item_id: UUID | str, completed: Decimal, target: Decimal,
                           photos: list[dict[str, str]] | None, notes: str | None) -> None:
        done = completed >= target
        await self.execute(
            """
            UPDATE work_plan_item SET
                completed_qty = :done_qty,
                progress_percent = LEAST(100, ROUND(:done_qty / NULLIF(target_qty, 0) * 100, 2)),
                status = CASE WHEN :is_done THEN 'DONE' WHEN :done_qty > 0 THEN 'IN_PROGRESS' ELSE 'TODO' END,
                realization_photos_json = COALESCE(CAST(:photos AS jsonb), realization_photos_json),
                notes = COALESCE(:notes, notes),
                update_at = now()
            WHERE item_id = CAST(:id AS uuid)
            """,
            {"id": str(item_id), "done_qty": completed, "is_done": done,
             "photos": json.dumps(photos) if photos is not None else None, "notes": notes},
        )

    async def missing_required_photos(self, item_id: UUID | str, requirement_ids: set[str]) -> list[str]:
        """Syarat foto wajib (image_requirement jenis pekerjaan item) yang belum dipenuhi."""
        rows = await self.fetchall(
            """
            SELECT ir.name, CAST(ir.image_requirement_id AS text) AS id
            FROM work_plan_item i JOIN image_requirement ir ON ir.work_type_id = i.work_type_id
            WHERE i.item_id = CAST(:id AS uuid) AND ir.is_mandatory AND ir.delete_at IS NULL
            ORDER BY ir.sort_order
            """,
            {"id": str(item_id)},
        )
        return [r.name for r in rows if r.id not in requirement_ids]

    async def existing_files(self, file_ids: list[str]) -> int:
        return int(await self.scalar(
            "SELECT COUNT(*) FROM file_object WHERE id = ANY(CAST(:ids AS uuid[]))", {"ids": list(set(file_ids))}
        ) or 0)

    async def request_rollover(self, item_id: UUID | str, reason: str, completed: Decimal) -> None:
        await self.execute(
            """
            UPDATE work_plan_item SET status = 'PENDING_ROLLOVER', rollover_approval_status = 'WAITING_PM',
                   delay_reason = :reason, completed_qty = :done_qty,
                   progress_percent = LEAST(100, ROUND(:done_qty / NULLIF(target_qty, 0) * 100, 2)), update_at = now()
            WHERE item_id = CAST(:id AS uuid)
            """,
            {"id": str(item_id), "reason": reason, "done_qty": completed},
        )

    async def reject_rollover(self, item_id: UUID | str, pm_id: str | None) -> None:
        await self.execute(
            "UPDATE work_plan_item SET status = CASE WHEN completed_qty > 0 THEN 'IN_PROGRESS' ELSE 'TODO' END, "
            "rollover_approval_status = 'REJECTED_BY_PM', approved_by_pm_id = CAST(:pm AS uuid), update_at = now() "
            "WHERE item_id = CAST(:id AS uuid)",
            {"id": str(item_id), "pm": pm_id},
        )

    async def shift(self, item_id: UUID | str, target_daily_id: UUID | str, pm_id: str | None) -> UUID:
        """Item asal → SHIFTED_DAY; item baru di jadwal tujuan membawa sisa volume (origin_item_id = asal).
        Prasyarat & penugasan ikut; foto realisasi & alasan tetap di item asal."""
        await self.execute(
            "UPDATE work_plan_item SET status = 'SHIFTED_DAY', rollover_approval_status = 'APPROVED_BY_PM', "
            "approved_by_pm_id = CAST(:pm AS uuid), shifted_to_daily_id = CAST(:target AS uuid), update_at = now() "
            "WHERE item_id = CAST(:id AS uuid)",
            {"id": str(item_id), "target": str(target_daily_id), "pm": pm_id},
        )
        new_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                                        completion_id, depends_on_item_id, target_qty, completed_qty, progress_percent,
                                        status, start_time, end_time, location_name, site_lat, site_lng,
                                        assigned_employee_ids, notes, origin_item_id)
            SELECT CAST(:target AS uuid), work_type_id, title, task_phase, is_main_deliverable, completion_id,
                   depends_on_item_id, target_qty - completed_qty, 0, 0, 'TODO', start_time, end_time, location_name,
                   site_lat, site_lng, assigned_employee_ids, notes, item_id
            FROM work_plan_item WHERE item_id = CAST(:id AS uuid)
            RETURNING item_id
            """,
            {"id": str(item_id), "target": str(target_daily_id)},
        )
        return new_id

    async def chain(self, item_id: UUID | str) -> list[Any]:
        """Rantai rollover lengkap (asal pertama → item aktif terakhir) yang memuat item ini."""
        return list(await self.fetchall(
            """
            WITH RECURSIVE up AS (
                SELECT item_id, origin_item_id FROM work_plan_item WHERE item_id = CAST(:id AS uuid)
                UNION ALL
                SELECT p.item_id, p.origin_item_id FROM work_plan_item p JOIN up ON p.item_id = up.origin_item_id
            ), root AS (SELECT item_id FROM up WHERE origin_item_id IS NULL),
            down AS (
                SELECT i.item_id FROM work_plan_item i JOIN root ON i.item_id = root.item_id
                UNION ALL
                SELECT c.item_id FROM work_plan_item c JOIN down ON c.origin_item_id = down.item_id
            )
            SELECT i.item_id, i.daily_plan_id, wpd.work_date, i.status, i.target_qty, i.completed_qty, i.delay_reason
            FROM down JOIN work_plan_item i ON i.item_id = down.item_id
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id
            ORDER BY wpd.work_date, i.create_at
            """,
            {"id": str(item_id)},
        ))

    async def archive(self, item_id: UUID | str) -> None:
        await self.execute(
            "UPDATE work_plan_item SET delete_at = now(), update_at = now() WHERE item_id = CAST(:id AS uuid)",
            {"id": str(item_id)},
        )

    async def log_decision(self, user_id: str, role: str, item_id: UUID | str, diff: dict[str, Any]) -> None:
        """Catatan keputusan PM ke app_activity_logs (delay_reason ketua tidak ditimpa, docs/35 §4)."""
        await self.execute(
            """
            INSERT INTO app_activity_logs (actor_user_id, actor_role, platform, action, entity_table, entity_id,
                                           changed_diff)
            VALUES (CAST(:uid AS uuid), :role, 'web_react', 'ROLLOVER_DECIDED', 'work_plan_item', CAST(:id AS uuid),
                    CAST(:diff AS jsonb))
            """,
            {"uid": user_id, "role": role[:30], "id": str(item_id), "diff": json.dumps(diff, default=str)},
        )

    async def target_day(self, daily_plan_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT daily_plan_id, work_date, team_id, division_id, status FROM work_plan_daily "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        )

    async def team_day(self, team_id: UUID | str, work_date: date) -> Any:
        return await self.fetchone(
            "SELECT daily_plan_id, work_date, team_id, division_id, status FROM work_plan_daily "
            "WHERE team_id = CAST(:t AS uuid) AND work_date = :d AND delete_at IS NULL",
            {"t": str(team_id), "d": work_date},
        )

    async def clone_day(self, source_daily_id: UUID | str, work_date: date, approver: str | None) -> UUID:
        """Jadwal baru di tanggal tujuan rollover: salin divisi, tim, lokasi, radius, jam; langsung disetujui PM."""
        new_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_daily (division_id, team_id, work_date, site_name, site_lat, site_lng,
                                         attendance_radius_m, clock_in_time, clock_out_time, status, created_by_id,
                                         approved_by_pm_id, approved_at)
            SELECT division_id, team_id, :d, site_name, site_lat, site_lng, attendance_radius_m, clock_in_time,
                   clock_out_time, 'APPROVED', COALESCE(CAST(:pm AS uuid), created_by_id), CAST(:pm AS uuid), now()
            FROM work_plan_daily WHERE daily_plan_id = CAST(:id AS uuid)
            RETURNING daily_plan_id
            """,
            {"id": str(source_daily_id), "d": work_date, "pm": approver},
        )
        return new_id
