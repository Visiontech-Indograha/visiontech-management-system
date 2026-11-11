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

from app.core.repository import BaseRepository, safe_columns

_SELECT = """
    SELECT i.item_id, i.daily_plan_id, wpd.work_date, i.work_type_id, wt.name AS work_type_name, i.title,
           i.task_phase, i.unit_measure, i.is_main_deliverable, i.completion_id, wc.project_title AS order_title,
           i.depends_on_item_id, dep.title AS depends_on_title, dep_team.name AS depends_on_team_name,
           -- Pekerjaan yang ditunggu sudah selesai? (mengikuti rantai pindah hari)
           (WITH RECURSIVE ch AS (
                SELECT dep.item_id, dep.status
                UNION ALL
                SELECT c.item_id, c.status FROM work_plan_item c JOIN ch ON c.origin_item_id = ch.item_id
                WHERE c.delete_at IS NULL)
            SELECT COALESCE(bool_or(ch.status = 'DONE'), FALSE) FROM ch
            WHERE ch.item_id IS NOT NULL) AS depends_on_done,
           i.target_qty, i.completed_qty, i.progress_percent,
           i.status, i.rollover_approval_status::text AS rollover_approval_status, i.approved_by_pm_id,
           i.origin_item_id, i.shifted_to_daily_id, i.delay_reason, i.notes, i.start_time, i.end_time,
           i.location_name, i.site_lat, i.site_lng, COALESCE(i.assigned_employee_ids, '[]'::jsonb)
               AS assigned_employee_ids, i.realization_photos_json, i.update_at
    FROM work_plan_item i
    JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id
    JOIN work_type wt ON wt.work_type_id = i.work_type_id
    LEFT JOIN work_completion wc ON wc.completion_id = i.completion_id
    LEFT JOIN work_plan_item dep ON dep.item_id = i.depends_on_item_id
    LEFT JOIN work_plan_daily dep_day ON dep_day.daily_plan_id = dep.daily_plan_id
    LEFT JOIN team dep_team ON dep_team.team_id = dep_day.team_id
"""

_FIELDS = ("work_type_id", "title", "task_phase", "unit_measure", "is_main_deliverable",
           "completion_id", "depends_on_item_id", "target_qty", "start_time", "end_time", "location_name",
           "site_lat", "site_lng", "notes")


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
            "target_qty, completed_qty, delay_reason FROM work_plan_item "
            "WHERE item_id = CAST(:id AS uuid) AND delete_at IS NULL "
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
            # Jenis titik survei hanya dipakai di dalam survei, bukan sebagai item jadwal.
            "SELECT CAST(division_id AS text) FROM work_type WHERE work_type_id = CAST(:id AS uuid) "
            "AND delete_at IS NULL AND kind <> 'SURVEY_POINT'",
            {"id": str(work_type_id)},
        )
        return str(val) if val else None

    async def work_type_kind(self, work_type_id: UUID | str) -> str | None:
        """Jenis (kind) jenis pekerjaan — menentukan fase default item."""
        val = await self.scalar(
            "SELECT kind FROM work_type WHERE work_type_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(work_type_id)},
        )
        return str(val) if val else None

    async def work_type_template(self, work_type_id: UUID | str) -> Any:
        """Bawaan jenis pekerjaan untuk item baru: kind, fase bawaan (NULL = ikut kind), dan satuan."""
        return await self.fetchone(
            "SELECT kind, default_phase, unit_measure FROM work_type "
            "WHERE work_type_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(work_type_id)},
        )

    async def user_division_ids(self, user_id: UUID | str) -> set[str]:
        """Divisi yang dipimpin/diurus pengguna (divisi karyawan + divisi tempat ia PM/OM)."""
        rows = await self.fetchall(
            """
            SELECT DISTINCT CAST(d.division_id AS text) AS division_id FROM users u
            JOIN employee e ON e.employee_id = u.employee_id
            JOIN division d ON d.delete_at IS NULL
                 AND (d.division_id = e.division_id OR d.pm_id = e.employee_id OR d.om_id = e.employee_id)
            WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL
            """,
            {"uid": str(user_id)},
        )
        return {r.division_id for r in rows}

    async def order_division(self, completion_id: UUID | str) -> Any:
        """(division_id, terbuka?) order klien."""
        return await self.fetchone(
            "SELECT CAST(division_id AS text) AS division_id, order_status NOT IN ('COMPLETED', 'CANCELLED') AS open "
            "FROM work_completion WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(completion_id)},
        )

    async def prerequisite(self, item_id: UUID | str) -> Any:
        """Item prasyarat: jadwal, tanggal, tim, lokasi, order/klien, dan `done` — DONE di item itu ATAU di item
        lanjutan rollover-nya (galian yang digeser ke hari lain selesai di item lanjutan, bukan item asal)."""
        return await self.fetchone(
            """
            WITH RECURSIVE chain AS (
                SELECT item_id, status FROM work_plan_item WHERE item_id = CAST(:id AS uuid)
                UNION ALL
                SELECT c.item_id, c.status FROM work_plan_item c JOIN chain ON c.origin_item_id = chain.item_id
                WHERE c.delete_at IS NULL
            )
            SELECT i.item_id, i.status, i.completion_id, wpd.work_date, wpd.team_id, wpd.division_id,
                   wpd.site_name, wc.client_name, t.name AS team_name,
                   EXISTS (SELECT 1 FROM chain WHERE chain.status = 'DONE') AS done
            FROM work_plan_item i
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = i.daily_plan_id
            LEFT JOIN team t ON t.team_id = wpd.team_id
            LEFT JOIN work_completion wc ON wc.completion_id = i.completion_id
            WHERE i.item_id = CAST(:id AS uuid) AND i.delete_at IS NULL AND wpd.delete_at IS NULL
            """,
            {"id": str(item_id)},
        )

    async def prerequisite_options(self, daily_plan_id: UUID | str) -> list[Any]:
        """Calon prasyarat: item tim sendiri 30 hari terakhir s.d. tanggal jadwal, plus item tim lain di lokasi yang
        sama (nama lokasi jadwal) pada rentang yang sama — urut tanggal terbaru."""
        return list(await self.fetchall(
            """
            SELECT i.item_id, i.title, i.task_phase, i.status, d.work_date, t.name AS team_name,
                   (d.team_id <> me.team_id) AS other_team
            FROM work_plan_daily me
            JOIN work_plan_daily d ON d.work_date BETWEEN me.work_date - 30 AND me.work_date AND d.delete_at IS NULL
                 AND (d.team_id = me.team_id OR lower(trim(d.site_name)) = lower(trim(me.site_name)))
            JOIN work_plan_item i ON i.daily_plan_id = d.daily_plan_id AND i.delete_at IS NULL
                 AND i.status <> 'SHIFTED_DAY' AND NOT (i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NOT NULL)
            LEFT JOIN team t ON t.team_id = d.team_id
            WHERE me.daily_plan_id = CAST(:id AS uuid)
            ORDER BY d.work_date DESC, (d.team_id <> me.team_id), i.create_at
            LIMIT 200
            """,
            {"id": str(daily_plan_id)},
        ))

    async def plan_site(self, daily_plan_id: UUID | str) -> str | None:
        site: str | None = await self.scalar(
            "SELECT site_name FROM work_plan_daily WHERE daily_plan_id = CAST(:id AS uuid)", {"id": str(daily_plan_id)})
        return site

    async def order_client(self, completion_id: UUID | str) -> str | None:
        client: str | None = await self.scalar(
            "SELECT client_name FROM work_completion WHERE completion_id = CAST(:id AS uuid)",
            {"id": str(completion_id)})
        return client

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
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, unit_measure,
                                        is_main_deliverable,
                                        completion_id, depends_on_item_id, target_qty, completed_qty, progress_percent,
                                        status, start_time, end_time, location_name, site_lat, site_lng,
                                        assigned_employee_ids, notes, origin_item_id, work_order_id)
            VALUES (CAST(:daily AS uuid), CAST(:work_type_id AS uuid), :title, :task_phase, :unit_measure,
                    :is_main_deliverable,
                    CAST(:completion_id AS uuid), CAST(:depends_on_item_id AS uuid), :target_qty, 0, 0, 'TODO',
                    CAST(:start_time AS time), CAST(:end_time AS time), :location_name,
                    CAST(:site_lat AS numeric), CAST(:site_lng AS numeric), CAST(:assigned_employee_ids AS jsonb),
                    :notes, CAST(:origin_item_id AS uuid),
                    (SELECT wc.work_order_id FROM work_completion wc
                     WHERE wc.completion_id = CAST(:completion_id AS uuid)))
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
        sets = ", ".join(f"{k} = CAST(:{k} AS {casts[k]})" if k in casts else f"{k} = :{k}" for k in safe_columns(sent))
        await self.execute(
            f"UPDATE work_plan_item SET {sets}, update_at = now() WHERE item_id = CAST(:id AS uuid)",
            {**_params({k: fields[k] for k in sent}), "id": str(item_id)},
        )

    async def set_progress(self, item_id: UUID | str, completed: Decimal, target: Decimal,
                           photos: list[dict[str, str | None]] | None, notes: str | None) -> None:
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

    async def done_items_photo_gaps(self, daily_plan_id: UUID | str) -> list[tuple[str, list[str]]]:
        """Pekerjaan DONE pada jadwal yang syarat foto wajibnya belum terpenuhi: [(judul, nama syarat), ...].
        Item survei dilewati (fotonya per titik survei, dicek di layanan survei)."""
        rows = await self.fetchall(
            """
            SELECT i.item_id, i.title, i.realization_photos_json
            FROM work_plan_item i
            WHERE i.daily_plan_id = CAST(:id AS uuid) AND i.delete_at IS NULL AND i.status = 'DONE'
              AND i.task_phase IS DISTINCT FROM 'SURVEY'
            ORDER BY i.title
            """,
            {"id": str(daily_plan_id)},
        )
        gaps: list[tuple[str, list[str]]] = []
        for row in rows:
            given = {str(p.get("requirement_id")) for p in (row.realization_photos_json or [])
                     if p.get("requirement_id")}
            missing = await self.missing_required_photos(row.item_id, given)
            if missing:
                gaps.append((row.title, missing))
        return gaps

    async def existing_files(self, file_ids: list[str]) -> int:
        return int(await self.scalar(
            "SELECT COUNT(*) FROM file_object WHERE id = ANY(CAST(:ids AS uuid[]))", {"ids": list(set(file_ids))}
        ) or 0)

    async def request_rollover(self, item_id: UUID | str, reason: str, completed: Decimal, expected: str) -> int:
        """Ajukan pindah hari hanya bila status item masih `expected` (compare-and-set). Kembalian = baris berubah."""
        result = await self.execute(
            """
            UPDATE work_plan_item SET status = 'PENDING_ROLLOVER', rollover_approval_status = 'WAITING_PM',
                   delay_reason = :reason, completed_qty = :done_qty,
                   progress_percent = LEAST(100, ROUND(:done_qty / NULLIF(target_qty, 0) * 100, 2)), update_at = now()
            WHERE item_id = CAST(:id AS uuid) AND status = :expected AND delete_at IS NULL
            """,
            {"id": str(item_id), "reason": reason, "done_qty": completed, "expected": expected},
        )
        return int(result.rowcount or 0)

    async def reject_rollover(self, item_id: UUID | str, pm_id: str | None, expected: str) -> int:
        """Tolak pindah hari hanya bila status item masih `expected`. Kembalian = baris berubah."""
        result = await self.execute(
            "UPDATE work_plan_item SET status = CASE WHEN completed_qty > 0 THEN 'IN_PROGRESS' ELSE 'TODO' END, "
            "rollover_approval_status = 'REJECTED_BY_PM', approved_by_pm_id = CAST(:pm AS uuid), update_at = now() "
            "WHERE item_id = CAST(:id AS uuid) AND status = :expected AND delete_at IS NULL",
            {"id": str(item_id), "pm": pm_id, "expected": expected},
        )
        return int(result.rowcount or 0)

    async def shift(
        self, item_id: UUID | str, target_daily_id: UUID | str, pm_id: str | None, expected: str
    ) -> UUID | None:
        """Item asal -> SHIFTED_DAY (hanya bila status masih `expected`; None bila sudah berubah); item baru di
        jadwal tujuan membawa sisa volume (origin_item_id = asal).
        Prasyarat & penugasan ikut; foto realisasi & alasan tetap di item asal."""
        moved = await self.execute(
            "UPDATE work_plan_item SET status = 'SHIFTED_DAY', rollover_approval_status = 'APPROVED_BY_PM', "
            "approved_by_pm_id = CAST(:pm AS uuid), shifted_to_daily_id = CAST(:target AS uuid), update_at = now() "
            "WHERE item_id = CAST(:id AS uuid) AND status = :expected AND delete_at IS NULL",
            {"id": str(item_id), "target": str(target_daily_id), "pm": pm_id, "expected": expected},
        )
        if not moved.rowcount:
            return None
        new_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                                        completion_id, depends_on_item_id, target_qty, completed_qty, progress_percent,
                                        status, start_time, end_time, location_name, site_lat, site_lng,
                                        assigned_employee_ids, notes, origin_item_id, work_order_id)
            SELECT CAST(:target AS uuid), work_type_id, title, task_phase, is_main_deliverable, completion_id,
                   depends_on_item_id, target_qty - completed_qty, 0, 0, 'TODO', start_time, end_time, location_name,
                   site_lat, site_lng, assigned_employee_ids, notes, item_id, work_order_id
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

    async def log_activity(
        self, user_id: str, role: str, action: str, item_id: UUID | str, diff: dict[str, Any]
    ) -> None:
        """Catatan perubahan item jadwal (misal saat hari APPROVED/ONGOING diubah) ke app_activity_logs."""
        await self.execute(
            """
            INSERT INTO app_activity_logs (actor_user_id, actor_role, platform, action, entity_table, entity_id,
                                           changed_diff)
            VALUES (CAST(:uid AS uuid), :role, 'web_react', :action, 'work_plan_item', CAST(:id AS uuid),
                    CAST(:diff AS jsonb))
            """,
            {
                "uid": user_id, "role": role[:30], "action": action,
                "id": str(item_id), "diff": json.dumps(diff, default=str),
            },
        )

    async def relink_dependents(self, old_item_id: UUID | str, new_item_id: UUID | str) -> int:
        """Alihkan item-item yang menunggu old_item ke new_item hasil rollover berantai."""
        result = await self.execute(
            """
            UPDATE work_plan_item
            SET depends_on_item_id = CAST(:new_id AS uuid), update_at = now()
            WHERE depends_on_item_id = CAST(:old_id AS uuid) AND delete_at IS NULL
            """,
            {"old_id": str(old_item_id), "new_id": str(new_item_id)},
        )
        return getattr(result, "rowcount", 0)

    async def team_division(self, team_id: UUID | str) -> str | None:
        """Cek divisi dari team_id."""
        val = await self.scalar(
            "SELECT CAST(division_id AS text) FROM team WHERE team_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(team_id)},
        )
        return str(val) if val else None

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

    async def clone_day(
        self,
        source_daily_id: UUID | str,
        work_date: date,
        approver: str | None,
        target_team_id: UUID | str | None = None,
    ) -> UUID:
        """Jadwal baru di tanggal tujuan rollover: salin divisi, tim (atau tim target), lokasi, radius, jam; disetujui PM."""  # noqa: E501
        new_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_daily (division_id, team_id, work_date, site_name, site_lat, site_lng,
                                         attendance_radius_m, clock_in_time, clock_out_time, status, created_by_id,
                                         approved_by_pm_id, approved_at)
            SELECT division_id, COALESCE(CAST(:target_team AS uuid), team_id), :d, site_name, site_lat, site_lng,
                   attendance_radius_m, clock_in_time, clock_out_time, 'APPROVED',
                   COALESCE(CAST(:pm AS uuid), created_by_id), CAST(:pm AS uuid), now()
            FROM work_plan_daily WHERE daily_plan_id = CAST(:id AS uuid)
            RETURNING daily_plan_id
            """,
            {
                "id": str(source_daily_id), "d": work_date, "pm": approver,
                "target_team": str(target_team_id) if target_team_id else None,
            },
        )
        return new_id
