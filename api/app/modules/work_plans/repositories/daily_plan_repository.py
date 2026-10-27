"""
app/modules/work_plans/repositories/daily_plan_repository.py
Jadwal harian daily-first (Master Schema V2): work_plan_daily N─1 division, N─1 team, N─1 employee (pembuat,
penyetuju); work_plan_daily 1─N work_plan_item, work_plan_attachment, attendance, asset_assignment.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT wpd.daily_plan_id, wpd.division_id, d.name AS division_name, wpd.team_id, t.name AS team_name,
           wpd.project_id, (SELECT p.project_title FROM project p WHERE p.project_id = wpd.project_id)
               AS project_title,
           t.leader_employee_id, le.full_name AS leader_name, le.phone_number AS leader_phone,
           d.pm_id, (SELECT pm.full_name FROM employee pm WHERE pm.employee_id = d.pm_id) AS pm_name,
           (SELECT pm.phone_number FROM employee pm WHERE pm.employee_id = d.pm_id) AS pm_phone,
           wpd.work_date, wpd.site_name, wpd.site_lat,
           wpd.site_lng, wpd.attendance_radius_m, wpd.clock_in_time, wpd.clock_out_time, wpd.status,
           wpd.created_by_id, wpd.approved_by_pm_id, wpd.approved_at, wpd.rejection_reason,
           (SELECT COUNT(*)::int FROM work_plan_item i WHERE i.daily_plan_id = wpd.daily_plan_id
              AND i.delete_at IS NULL AND NOT (i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NOT NULL))
              AS item_count,
           (SELECT COUNT(*)::int FROM work_plan_item i WHERE i.daily_plan_id = wpd.daily_plan_id
              AND i.delete_at IS NULL AND i.status = 'DONE'
              AND NOT (i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NOT NULL)) AS done_count,
           -- Persen progres nyata: rata-rata (jumlah dikerjakan / target) per pekerjaan, DONE = 100%.
           (SELECT COALESCE(ROUND(AVG(CASE WHEN i.status = 'DONE' THEN 1
                        ELSE LEAST(COALESCE(i.completed_qty, 0) / NULLIF(i.target_qty, 0), 1) END) * 100), 0)::int
              FROM work_plan_item i WHERE i.daily_plan_id = wpd.daily_plan_id AND i.delete_at IS NULL
              AND i.status <> 'SHIFTED_DAY'
              AND NOT (i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NOT NULL)) AS progress_pct,
           -- Jenis pekerjaan hari itu (Survei/Persiapan/Instalasi/Replacement/Maintenance) untuk filter & warna.
           ARRAY(SELECT DISTINCT i.task_phase::text FROM work_plan_item i
                 WHERE i.daily_plan_id = wpd.daily_plan_id AND i.delete_at IS NULL) AS phases
    FROM work_plan_daily wpd
    JOIN division d ON d.division_id = wpd.division_id
    JOIN team t ON t.team_id = wpd.team_id
    JOIN employee le ON le.employee_id = t.leader_employee_id
"""


class DailyPlanRepository(BaseRepository):
    async def project_window(self, project_id: UUID | str) -> Any:
        """Divisi, status & rentang tanggal proyek (validasi jadwal yang dikaitkan)."""
        return await self.fetchone(
            "SELECT division_id, status, start_date, end_date FROM project "
            "WHERE project_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(project_id)},
        )

    """Query work_plan_daily dan rujukannya."""

    async def list_plans(
        self,
        *,
        start: date,
        end: date,
        division_id: UUID | None,
        team_id: UUID | None,
        status: str | None,
        managed_by: str | None,
        field_employee: str | None,
    ) -> list[Any]:
        """Jadwal dalam rentang tanggal. `managed_by`: hanya divisi yang PM/OM-nya karyawan ini;
        `field_employee`: hanya tim karyawan ini dan yang sudah dirilis ke lapangan."""
        return list(await self.fetchall(
            _SELECT + """
            WHERE wpd.delete_at IS NULL AND wpd.work_date BETWEEN :start AND :end
              AND (CAST(:div AS uuid) IS NULL OR wpd.division_id = CAST(:div AS uuid))
              AND (CAST(:team AS uuid) IS NULL OR wpd.team_id = CAST(:team AS uuid))
              AND (CAST(:status AS varchar) IS NULL OR wpd.status = CAST(:status AS varchar))
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (d.pm_id, d.om_id))
              AND (CAST(:field AS uuid) IS NULL OR (
                    wpd.status IN ('APPROVED', 'ONGOING', 'COMPLETED')
                    AND EXISTS (SELECT 1 FROM member m WHERE m.team_id = wpd.team_id
                                AND m.employee_id = CAST(:field AS uuid) AND m.is_active AND m.delete_at IS NULL)))
            ORDER BY wpd.work_date, d.name, t.name
            """,
            {"start": start, "end": end, "div": str(division_id) if division_id else None,
             "team": str(team_id) if team_id else None, "status": status, "mgr": managed_by,
             "field": field_employee},
        ))

    async def get(self, daily_plan_id: UUID | str) -> Any:
        return await self.fetchone(
            _SELECT + " WHERE wpd.daily_plan_id = CAST(:id AS uuid) AND wpd.delete_at IS NULL",
            {"id": str(daily_plan_id)},
        )

    async def items(self, daily_plan_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT i.item_id, i.title, i.task_phase, i.work_type_id, wt.name AS work_type_name, i.completion_id,
                   i.depends_on_item_id,
                   i.location_name, i.target_qty, i.completed_qty, i.status,
                   i.rollover_approval_status::text AS rollover_approval_status, i.delay_reason
            FROM work_plan_item i
            JOIN work_type wt ON wt.work_type_id = i.work_type_id
            WHERE i.daily_plan_id = CAST(:id AS uuid) AND i.delete_at IS NULL
            ORDER BY i.start_time NULLS LAST, i.create_at
            """,
            {"id": str(daily_plan_id)},
        ))

    async def attachment_ids(self, daily_plan_id: UUID | str) -> list[UUID]:
        rows = await self.fetchall(
            "SELECT file_id FROM work_plan_attachment WHERE daily_plan_id = CAST(:id AS uuid) ORDER BY sort_order",
            {"id": str(daily_plan_id)},
        )
        return [r.file_id for r in rows]

    async def team_of_division(self, team_id: UUID | str, division_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM team WHERE team_id = CAST(:t AS uuid) AND division_id = CAST(:d AS uuid) "
            "AND delete_at IS NULL AND status)",
            {"t": str(team_id), "d": str(division_id)},
        ))

    async def team_day_taken(self, team_id: UUID | str, work_date: date, exclude: UUID | str | None = None) -> bool:
        """Satu jadwal per tim per tanggal (titik absen tim hari itu)."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM work_plan_daily WHERE team_id = CAST(:t AS uuid) AND work_date = :d
                           AND delete_at IS NULL AND (CAST(:ex AS uuid) IS NULL OR daily_plan_id <> CAST(:ex AS uuid)))
            """,
            {"t": str(team_id), "d": work_date, "ex": str(exclude) if exclude else None},
        ))

    async def insert(self, fields: dict[str, Any]) -> UUID:
        daily_plan_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_daily (division_id, team_id, project_id, work_date, site_name, site_lat, site_lng,
                                         attendance_radius_m, clock_in_time, clock_out_time, status, created_by_id)
            VALUES (CAST(:division_id AS uuid), CAST(:team_id AS uuid), CAST(:project_id AS uuid), :work_date,
                    :site_name, :site_lat, :site_lng, :attendance_radius_m, :clock_in_time, :clock_out_time, 'DRAFT',
                    CAST(:created_by_id AS uuid))
            RETURNING daily_plan_id
            """,
            {"project_id": None, **fields},
        )
        return daily_plan_id

    async def update(self, daily_plan_id: UUID | str, fields: dict[str, Any]) -> None:
        await self.execute(
            """
            UPDATE work_plan_daily SET
                team_id = COALESCE(CAST(:team_id AS uuid), team_id),
                project_id = COALESCE(CAST(:project_id AS uuid), project_id),
                work_date = COALESCE(CAST(:work_date AS date), work_date),
                site_name = CASE WHEN :site_name_set THEN :site_name ELSE site_name END,
                site_lat = CASE WHEN :site_lat_set THEN CAST(:site_lat AS numeric) ELSE site_lat END,
                site_lng = CASE WHEN :site_lng_set THEN CAST(:site_lng AS numeric) ELSE site_lng END,
                attendance_radius_m = CASE WHEN :attendance_radius_m_set
                                            THEN CAST(:attendance_radius_m AS int)
                                            ELSE attendance_radius_m END,
                clock_in_time = COALESCE(CAST(:clock_in_time AS time), clock_in_time),
                clock_out_time = COALESCE(CAST(:clock_out_time AS time), clock_out_time),
                update_at = now()
            WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {**fields, "id": str(daily_plan_id)},
        )

    async def set_status(
        self,
        daily_plan_id: UUID | str,
        status: str,
        *,
        approver: str | None = None,
        rejection_reason: str | None = None,
    ) -> None:
        """Perpindahan status. APPROVED mencatat penyetuju; DRAFT dari penolakan mencatat alasannya;
        pengajuan ulang menghapus alasan lama."""
        await self.execute(
            """
            UPDATE work_plan_daily SET
                status = CAST(:status AS varchar),
                approved_by_pm_id = CASE WHEN CAST(:status AS varchar) = 'APPROVED' THEN CAST(:approver AS uuid)
                                         WHEN CAST(:status AS varchar) = 'DRAFT' THEN NULL ELSE approved_by_pm_id END,
                approved_at = CASE WHEN CAST(:status AS varchar) = 'APPROVED' THEN now()
                                   WHEN CAST(:status AS varchar) = 'DRAFT' THEN NULL ELSE approved_at END,
                rejection_reason = CASE WHEN CAST(:status AS varchar) = 'DRAFT' THEN CAST(:reason AS text)
                                        WHEN CAST(:status AS varchar) = 'SUBMITTED' THEN NULL
                                        ELSE rejection_reason END,
                update_at = now()
            WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(daily_plan_id), "status": status, "approver": approver, "reason": rejection_reason},
        )

    async def has_activity(self, daily_plan_id: UUID | str) -> bool:
        """Jadwal yang sudah dipakai absensi atau peminjaman aset tidak boleh dihapus."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM attendance WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL)
                OR EXISTS (SELECT 1 FROM asset_assignment WHERE daily_plan_id = CAST(:id AS uuid)
                           AND delete_at IS NULL)
            """,
            {"id": str(daily_plan_id)},
        ))

    async def archive(self, daily_plan_id: UUID | str) -> None:
        await self.execute(
            "UPDATE work_plan_item SET delete_at = now(), update_at = now() "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        )
        await self.execute(
            "UPDATE work_plan_daily SET delete_at = now(), update_at = now() "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        )

    async def replace_attachments(self, daily_plan_id: UUID | str, file_ids: list[UUID]) -> None:
        await self.execute(
            "DELETE FROM work_plan_attachment WHERE daily_plan_id = CAST(:id AS uuid)", {"id": str(daily_plan_id)}
        )
        for order, file_id in enumerate(dict.fromkeys(file_ids)):
            await self.execute(
                "INSERT INTO work_plan_attachment (daily_plan_id, file_id, sort_order) "
                "VALUES (CAST(:id AS uuid), CAST(:f AS uuid), :o)",
                {"id": str(daily_plan_id), "f": str(file_id), "o": order},
            )

    async def existing_files(self, file_ids: list[UUID]) -> int:
        return int(await self.scalar(
            "SELECT COUNT(*) FROM file_object WHERE id = ANY(CAST(:ids AS uuid[]))",
            {"ids": [str(f) for f in set(file_ids)]},
        ) or 0)

    # ── Pilihan formulir ───────────────────────────────────────────────────────
    async def divisions(self, managed_by: str | None) -> list[Any]:
        return list(await self.fetchall(
            "SELECT division_id, name FROM division WHERE delete_at IS NULL AND status "
            "AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (pm_id, om_id)) ORDER BY name",
            {"mgr": managed_by},
        ))

    async def teams(self, managed_by: str | None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT t.team_id, t.name, t.division_id, t.leader_employee_id, e.full_name AS leader_name
            FROM team t JOIN division d ON d.division_id = t.division_id
            JOIN employee e ON e.employee_id = t.leader_employee_id
            WHERE t.delete_at IS NULL AND t.status AND d.delete_at IS NULL
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (d.pm_id, d.om_id))
            ORDER BY d.name, t.name
            """,
            {"mgr": managed_by},
        ))

    async def open_orders(self, managed_by: str | None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT wc.completion_id, wc.client_name, wc.project_title, wc.order_number, wc.division_id
            FROM work_completion wc LEFT JOIN division d ON d.division_id = wc.division_id
            WHERE wc.delete_at IS NULL AND wc.order_status NOT IN ('COMPLETED', 'CANCELLED')
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (wc.pm_id, d.pm_id, d.om_id))
            ORDER BY wc.create_at DESC
            """,
            {"mgr": managed_by},
        ))

    async def plans_of_order(self, completion_id: UUID | str) -> list[Any]:
        """Jadwal yang memuat item order ini (proyek multi-minggu dilacak per hari/titik)."""
        return list(await self.fetchall(
            _SELECT + """
            WHERE wpd.delete_at IS NULL AND EXISTS (
                SELECT 1 FROM work_plan_item i WHERE i.daily_plan_id = wpd.daily_plan_id
                AND i.completion_id = CAST(:c AS uuid) AND i.delete_at IS NULL)
            ORDER BY wpd.work_date
            """,
            {"c": str(completion_id)},
        ))

    async def has_daily_report(self, daily_plan_id: UUID | str) -> bool:
        """Apakah laporan harian sudah ada dan belum dihapus."""
        val = await self.scalar(
            "SELECT 1 FROM work_plan_daily_report WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        )
        return bool(val)

    async def get_daily_report(self, daily_plan_id: UUID | str) -> Any:
        """Mengambil data laporan harian jadwal kerja."""
        return await self.fetchone(
            """
            SELECT r.report_id, r.daily_plan_id, r.leader_employee_id, e.full_name AS leader_name,
                   r.summary, r.obstacles, r.photos_json, r.submitted_at, r.create_at
            FROM work_plan_daily_report r
            LEFT JOIN employee e ON e.employee_id = r.leader_employee_id
            WHERE r.daily_plan_id = CAST(:id AS uuid) AND r.delete_at IS NULL
            """,
            {"id": str(daily_plan_id)},
        )

    async def create_daily_report(
        self,
        daily_plan_id: UUID | str,
        leader_id: UUID | str,
        summary: str,
        obstacles: str | None,
        photos: list[Any],
    ) -> UUID:
        """Membuat atau memperbarui laporan harian ketua tim."""
        import json
        sql = """
            INSERT INTO work_plan_daily_report (
                daily_plan_id, leader_employee_id, summary, obstacles, photos_json, submitted_at
            ) VALUES (
                CAST(:did AS uuid), CAST(:lid AS uuid), :summary, :obstacles, CAST(:photos AS jsonb), now()
            )
            ON CONFLICT (daily_plan_id) DO UPDATE SET
                leader_employee_id = EXCLUDED.leader_employee_id,
                summary = EXCLUDED.summary,
                obstacles = EXCLUDED.obstacles,
                photos_json = EXCLUDED.photos_json,
                submitted_at = now(),
                update_at = now(),
                delete_at = NULL
            RETURNING report_id
        """
        report_id: UUID = await self.scalar(
            sql,
            {
                "did": str(daily_plan_id),
                "lid": str(leader_id),
                "summary": summary.strip(),
                "obstacles": obstacles.strip() if obstacles else None,
                "photos": json.dumps(photos),
            },
        )
        return report_id

    async def active_leader_plan_without_report(
        self, employee_id: UUID | str, work_date: date
    ) -> UUID | None:
        """Cari apakah karyawan adalah ketua tim pada jadwal harian hari ini yang belum memiliki laporan."""
        sql = """
            SELECT wpd.daily_plan_id
            FROM work_plan_daily wpd
            JOIN team t ON t.team_id = wpd.team_id
            WHERE t.leader_employee_id = CAST(:eid AS uuid)
              AND wpd.work_date = :wdate
              AND wpd.status IN ('APPROVED', 'ONGOING')
              AND wpd.delete_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM work_plan_daily_report r
                  WHERE r.daily_plan_id = wpd.daily_plan_id AND r.delete_at IS NULL
              )
            LIMIT 1
        """
        val = await self.scalar(sql, {"eid": str(employee_id), "wdate": work_date})
        return UUID(str(val)) if val is not None else None

    async def team_standing(self, team_id: UUID | str) -> Any:
        """Ambil informasi tim aktif."""
        return await self.fetchone(
            "SELECT team_id, name, division_id, leader_employee_id FROM team "
            "WHERE team_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(team_id)},
        )

    async def get_weekly_reports_for_team(
        self, team_id: UUID | str, start_date: date, end_date: date
    ) -> list[Any]:
        """Ambil seluruh laporan harian tim dalam rentang 1 minggu (Senin-Sabtu) untuk meeting mingguan."""
        return list(await self.fetchall(
            """
            SELECT r.report_id, r.daily_plan_id, r.leader_employee_id, e.full_name AS leader_name,
                   r.summary, r.obstacles, r.photos_json, r.submitted_at, r.create_at,
                   wpd.work_date, wpd.status as plan_status
            FROM work_plan_daily_report r
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = r.daily_plan_id
            LEFT JOIN employee e ON e.employee_id = r.leader_employee_id
            WHERE wpd.team_id = CAST(:team AS uuid)
              AND wpd.work_date BETWEEN :start AND :end
              AND r.delete_at IS NULL AND wpd.delete_at IS NULL
            ORDER BY wpd.work_date ASC
            """,
            {"team": str(team_id), "start": start_date, "end": end_date},
        ))

