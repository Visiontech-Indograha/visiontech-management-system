"""
app/modules/work_plans/repositories/daily_plan_repository.py
Jadwal harian daily-first (Master Schema V2): work_plan_daily N─1 division, N─1 team, N─1 employee (pembuat,
penyetuju); work_plan_daily 1─N work_plan_item, work_plan_attachment, attendance, asset_assignment.
"""
from __future__ import annotations

import json
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
           wpd.site_lng, wpd.attendance_radius_m, wpd.clock_in_time, wpd.clock_out_time, wpd.status, wpd.kind,
           wpd.created_by_id, wpd.approved_by_pm_id, wpd.approved_at, wpd.rejection_reason,
           (SELECT COUNT(*)::int FROM work_plan_item i WHERE i.daily_plan_id = wpd.daily_plan_id
              AND i.delete_at IS NULL AND NOT (i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NOT NULL))
              AS item_count,
           (SELECT COUNT(*)::int FROM work_plan_item i WHERE i.daily_plan_id = wpd.daily_plan_id
              AND i.delete_at IS NULL AND i.status = 'DONE'
              AND NOT (i.task_phase = 'SURVEY' AND i.depends_on_item_id IS NOT NULL)) AS done_count,
           -- Persen progres nyata: rata-rata (jumlah dikerjakan / target) per pekerjaan, DONE = 100%.
           -- Item yang dipindah hari (SHIFTED_DAY) tak dihitung, sehingga bisa 100 walau masih ada item lain
           -- yang belum selesai: 100 hanya bila SEMUA item DONE (selaras item_count/done_count & web displayPct).
           (SELECT CASE WHEN EXISTS (SELECT 1 FROM work_plan_item a WHERE a.daily_plan_id = wpd.daily_plan_id
                          AND a.delete_at IS NULL
                          AND NOT (a.task_phase = 'SURVEY' AND a.depends_on_item_id IS NOT NULL))
                    AND NOT EXISTS (SELECT 1 FROM work_plan_item a WHERE a.daily_plan_id = wpd.daily_plan_id
                          AND a.delete_at IS NULL AND a.status <> 'DONE'
                          AND NOT (a.task_phase = 'SURVEY' AND a.depends_on_item_id IS NOT NULL))
                  THEN 100
                  ELSE LEAST(99, COALESCE(ROUND(AVG(CASE WHEN i.status = 'DONE' THEN 1
                        ELSE LEAST(COALESCE(i.completed_qty, 0) / NULLIF(i.target_qty, 0), 1) END) * 100), 0)::int)
             END
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

    async def recent_sites(self, *, team_id: UUID, managed_by: str | None, limit: int) -> list[Any]:
        """Lokasi (nama + koordinat) jadwal terakhir sebuah tim, terbaru dulu, tanpa duplikat."""
        return list(await self.fetchall(
            """
            SELECT wpd.site_name, wpd.site_lat, wpd.site_lng, wpd.attendance_radius_m,
                   MAX(wpd.work_date) AS last_used
            FROM work_plan_daily wpd JOIN division d ON d.division_id = wpd.division_id
            WHERE wpd.delete_at IS NULL AND wpd.team_id = CAST(:team AS uuid)
              AND wpd.site_name IS NOT NULL AND wpd.site_lat IS NOT NULL AND wpd.site_lng IS NOT NULL
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (d.pm_id, d.om_id))
            GROUP BY wpd.site_name, wpd.site_lat, wpd.site_lng, wpd.attendance_radius_m
            ORDER BY last_used DESC, wpd.site_name
            LIMIT :lim
            """,
            {"team": str(team_id), "mgr": managed_by, "lim": limit},
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

    async def team_leader(self, team_id: UUID | str) -> str | None:
        """Karyawan ketua tim (untuk peringatan cuti pada alokasi massal)."""
        value = await self.scalar("SELECT leader_employee_id FROM team WHERE team_id = CAST(:t AS uuid)",
                                  {"t": str(team_id)})
        return str(value) if value else None

    async def weekly_items(self, daily_plan_ids: list[str]) -> list[Any]:
        """Item (pekerjaan) dari jadwal-jadwal matriks mingguan, urut mulai kerja."""
        if not daily_plan_ids:
            return []
        return list(await self.fetchall(
            """
            SELECT i.daily_plan_id, i.item_id, i.title, wt.name AS work_type_name, i.completion_id,
                   i.target_qty, i.completed_qty, i.status
            FROM work_plan_item i
            LEFT JOIN work_type wt ON wt.work_type_id = i.work_type_id
            WHERE i.daily_plan_id = ANY(CAST(:ids AS uuid[])) AND i.delete_at IS NULL
            ORDER BY i.start_time NULLS LAST, i.create_at
            """,
            {"ids": daily_plan_ids},
        ))

    async def orders_brief(self, completion_ids: list[str]) -> list[Any]:
        """Order klien beserta total target, target selesai (item utama), dan target yang sudah dijadwalkan."""
        if not completion_ids:
            return []
        return list(await self.fetchall(
            """
            SELECT wc.completion_id, wc.client_name, wc.project_title, wc.order_number, wc.total_target_unit,
                   COALESCE((SELECT SUM(wpi.completed_qty)::int FROM work_plan_item wpi
                             WHERE wpi.completion_id = wc.completion_id AND wpi.is_main_deliverable = TRUE
                               AND wpi.delete_at IS NULL), 0) AS completed_target_unit,
                   COALESCE((SELECT SUM(i.target_qty)::float FROM work_plan_item i
                             JOIN work_plan_daily d ON d.daily_plan_id = i.daily_plan_id AND d.delete_at IS NULL
                             WHERE i.completion_id = wc.completion_id AND i.delete_at IS NULL), 0) AS scheduled_qty
            FROM work_completion wc
            WHERE wc.completion_id = ANY(CAST(:ids AS uuid[])) AND wc.delete_at IS NULL
            """,
            {"ids": completion_ids},
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

    async def leader_on_leave(self, employee_id: str, work_date: date) -> bool:
        """Ketua tim punya permohonan cuti aktif/pending yang mencakup tanggal itu (peringatan alokasi massal)."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (SELECT 1 FROM leave_request
                           WHERE employee_id = CAST(:emp AS uuid) AND delete_at IS NULL
                             AND status IN ('PENDING', 'APPROVED_BY_PM', 'APPROVED_BY_HR')
                             AND start_date <= :d AND end_date >= :d)
            """,
            {"emp": employee_id, "d": work_date},
        ))

    async def asset_loan_conflict(self, asset_type: str, asset_id: UUID | str, work_date: date) -> Any:
        """Peminjaman aset yang bentrok pada tanggal itu: peminjaman tanpa jadwal atau berjadwal pada tanggal sama.
        Mengembalikan baris (nama tim pemegang) atau None."""
        if asset_type == "TOOL":
            sql = """
                SELECT t.name AS team_name FROM asset_assignment aa
                LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = aa.daily_plan_id AND wpd.delete_at IS NULL
                LEFT JOIN team t ON t.team_id = wpd.team_id
                WHERE aa.tool_id = CAST(:id AS uuid) AND aa.returned_at IS NULL AND aa.delete_at IS NULL
                  AND (aa.daily_plan_id IS NULL OR wpd.work_date = CAST(:d AS date))
                ORDER BY aa.loaned_at DESC LIMIT 1
            """
        else:
            sql = """
                SELECT t.name AS team_name FROM asset_assignment aa
                LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = aa.daily_plan_id AND wpd.delete_at IS NULL
                LEFT JOIN team t ON t.team_id = wpd.team_id
                WHERE aa.vehicle_id = CAST(:id AS uuid) AND aa.returned_at IS NULL AND aa.delete_at IS NULL
                  AND (aa.daily_plan_id IS NULL OR wpd.work_date = CAST(:d AS date))
                ORDER BY aa.loaned_at DESC LIMIT 1
            """
        return await self.fetchone(sql, {"id": str(asset_id), "d": work_date})

    async def set_kind(self, daily_plan_id: UUID | str, kind: str) -> None:
        """Ubah jenis jadwal (STANDBY ↔ WORK); dipakai aktivasi siaga."""
        await self.execute(
            "UPDATE work_plan_daily SET kind = :kind, update_at = NOW() "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id), "kind": kind},
        )

    async def insert(self, fields: dict[str, Any]) -> UUID:
        daily_plan_id: UUID = await self.scalar(
            """
            INSERT INTO work_plan_daily (division_id, team_id, project_id, work_date, site_name, site_lat, site_lng,
                                         attendance_radius_m, clock_in_time, clock_out_time, status, kind,
                                         created_by_id)
            VALUES (CAST(:division_id AS uuid), CAST(:team_id AS uuid), CAST(:project_id AS uuid), :work_date,
                    :site_name, :site_lat, :site_lng, :attendance_radius_m, :clock_in_time, :clock_out_time, 'DRAFT',
                    :kind, CAST(:created_by_id AS uuid))
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

    async def release_plan_assets(self, daily_plan_id: UUID | str) -> None:
        """Jadwal selesai: peminjaman alat/kendaraan yang masih berjalan untuk jadwal ini otomatis dikembalikan
        (siap dipakai lagi). Status aset dikembalikan ke `ready` bila tidak ada peminjaman lain yang berjalan."""
        released = await self.fetchall(
            "UPDATE asset_assignment SET returned_at = now(), assignment_status = 'ready' "
            "WHERE daily_plan_id = CAST(:id AS uuid) AND returned_at IS NULL AND delete_at IS NULL "
            "RETURNING tool_id, vehicle_id",
            {"id": str(daily_plan_id)},
        )
        for row in released:
            if row.tool_id is not None:
                await self.execute(
                    "UPDATE tool SET status = 'ready', update_at = now() WHERE tool_id = CAST(:id AS uuid) "
                    "AND status IN ('allocated', 'loaned') AND NOT EXISTS (SELECT 1 FROM asset_assignment "
                    "WHERE tool_id = CAST(:id AS uuid) AND returned_at IS NULL AND delete_at IS NULL)",
                    {"id": str(row.tool_id)},
                )
            if row.vehicle_id is not None:
                await self.execute(
                    "UPDATE vehicle SET status = 'ready', update_at = now() WHERE vehicle_id = CAST(:id AS uuid) "
                    "AND status IN ('allocated', 'loaned') AND NOT EXISTS (SELECT 1 FROM asset_assignment "
                    "WHERE vehicle_id = CAST(:id AS uuid) AND returned_at IS NULL AND delete_at IS NULL)",
                    {"id": str(row.vehicle_id)},
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

    async def log_audit(self, user_id: str, role: str, daily_plan_id: UUID | str, action: str,
                        diff: dict[str, Any]) -> None:
        """Jejak audit jadwal harian (mis. BACKDATE_CREATED, BACKDATE_APPROVED) ke app_activity_logs."""
        await self.execute(
            """
            INSERT INTO app_activity_logs (actor_user_id, actor_role, platform, action, entity_table, entity_id,
                                           changed_diff)
            VALUES (CAST(:uid AS uuid), :role, 'web_react', :action, 'work_plan_daily', CAST(:id AS uuid),
                    CAST(:diff AS jsonb))
            """,
            {"uid": user_id, "role": (role or "")[:30], "action": action, "id": str(daily_plan_id),
             "diff": json.dumps(diff, default=str)},
        )

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

    async def teams(self, managed_by: str | None, division_id: UUID | str | None = None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT t.team_id, t.name, t.division_id, t.leader_employee_id, e.full_name AS leader_name
            FROM team t JOIN division d ON d.division_id = t.division_id
            JOIN employee e ON e.employee_id = t.leader_employee_id
            WHERE t.delete_at IS NULL AND t.status AND d.delete_at IS NULL
              AND (CAST(:mgr AS uuid) IS NULL OR CAST(:mgr AS uuid) IN (d.pm_id, d.om_id))
              AND (CAST(:div AS uuid) IS NULL OR t.division_id = CAST(:div AS uuid))
            ORDER BY d.name, t.name
            """,
            {"mgr": managed_by, "div": str(division_id) if division_id else None},
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

    async def order_scope(self, completion_id: UUID | str) -> Any:
        """PM order & PM/OM divisinya; None bila order tidak ada / sudah dihapus."""
        return await self.fetchone(
            """
            SELECT wc.pm_id, d.pm_id AS div_pm_id, d.om_id AS div_om_id
            FROM work_completion wc JOIN division d ON d.division_id = wc.division_id
            WHERE wc.completion_id = CAST(:c AS uuid) AND wc.delete_at IS NULL
            """,
            {"c": str(completion_id)},
        )

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

    async def order_target_totals(self, completion_id: UUID | str) -> Any:
        """Target total & selesai order (selesai = item utama, seperti ringkasan order) serta target yang terjadwal."""
        return await self.fetchone(
            """
            SELECT wc.total_target_unit,
                   COALESCE((SELECT SUM(wpi.completed_qty)::int FROM work_plan_item wpi
                             WHERE wpi.completion_id = wc.completion_id AND wpi.is_main_deliverable = TRUE
                               AND wpi.delete_at IS NULL), 0) AS completed_target_unit,
                   COALESCE((SELECT SUM(i.target_qty)::float FROM work_plan_item i
                             JOIN work_plan_daily d ON d.daily_plan_id = i.daily_plan_id AND d.delete_at IS NULL
                             WHERE i.completion_id = wc.completion_id AND i.delete_at IS NULL),
                            0) AS scheduled_target_qty
            FROM work_completion wc
            WHERE wc.completion_id = CAST(:c AS uuid) AND wc.delete_at IS NULL
            """,
            {"c": str(completion_id)},
        )

    async def count_items(self, daily_plan_id: UUID | str) -> int:
        """Jumlah item jadwal yang belum dihapus (jadwal tanpa item tidak boleh diajukan/disetujui)."""
        return int(await self.scalar(
            "SELECT count(*) FROM work_plan_item WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(daily_plan_id)},
        ) or 0)

    async def has_pending_rollover(self, daily_plan_id: UUID | str) -> bool:
        """Ada item yang menunggu keputusan pemindahan hari (PENDING_ROLLOVER) — jadwal belum boleh ditutup."""
        return bool(await self.scalar(
            "SELECT 1 FROM work_plan_item WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL "
            "AND status = 'PENDING_ROLLOVER' LIMIT 1",
            {"id": str(daily_plan_id)},
        ))

    async def leader_checked_in(self, daily_plan_id: UUID | str, today: date) -> bool:
        """Ketua tim sudah absen masuk pada tanggal jadwal ATAU pada hari ini (WIB), absensi yang belum dihapus.

        Jadwal bertanggal lampau yang belum dimulai boleh dimulai bila ketua sudah absen hari ini (F11)."""
        return bool(await self.scalar(
            """
            SELECT 1 FROM work_plan_daily wpd
            JOIN team t ON t.team_id = wpd.team_id
            JOIN attendance a ON a.employee_id = t.leader_employee_id
                             AND a.attendance_date IN (wpd.work_date, CAST(:today AS date))
            WHERE wpd.daily_plan_id = CAST(:id AS uuid) AND a.delete_at IS NULL
            LIMIT 1
            """,
            {"id": str(daily_plan_id), "today": today},
        ))

    async def copy_items(self, source_id: UUID | str, target_id: UUID | str) -> None:
        """Salin item jadwal ke jadwal lain (hari lain). Progres direset; item survei dan item yang bergantung
        pada prasyarat (depends_on_item_id) dilewati karena konteks harinya tidak ikut disalin."""
        await self.execute(
            """
            INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, is_main_deliverable,
                                        completion_id, target_qty, completed_qty, progress_percent, status,
                                        start_time, end_time, location_name, site_lat, site_lng,
                                        assigned_employee_ids, notes)
            SELECT CAST(:target AS uuid), i.work_type_id, i.title, i.task_phase, i.is_main_deliverable,
                   i.completion_id, i.target_qty, 0, 0, 'TODO', i.start_time, i.end_time, i.location_name,
                   i.site_lat, i.site_lng, i.assigned_employee_ids, i.notes
            FROM work_plan_item i
            WHERE i.daily_plan_id = CAST(:source AS uuid) AND i.delete_at IS NULL
              AND i.task_phase <> 'SURVEY' AND i.depends_on_item_id IS NULL
            ORDER BY i.start_time NULLS LAST, i.create_at
            """,
            {"source": str(source_id), "target": str(target_id)},
        )

    async def has_open_correction(self, daily_plan_id: UUID | str) -> bool:
        """Ada koreksi laporan yang belum diputuskan akhir (diminta, direvisi, atau menunggu tinjauan)."""
        val = await self.scalar(
            "SELECT 1 FROM daily_report_correction WHERE daily_plan_id = CAST(:id AS uuid) AND delete_at IS NULL "
            "AND status IN ('REQUESTED', 'REVISING', 'IN_REVIEW') LIMIT 1",
            {"id": str(daily_plan_id)},
        )
        return bool(val)

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
                "obstacles": obstacles.strip() if obstacles and obstacles.strip() else None,
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

