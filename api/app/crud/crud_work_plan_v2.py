"""
api/app/crud/crud_work_plan_v2.py
Akses data database statis ANSI SQL untuk Work Plan V2:
- Form Options V2
- CRUD work_plan_weekly
- CRUD work_plan_daily
- CRUD work_plan_item
Mengikuti aturan SQL statis, parameter binding, CAST(:x AS type), dan soft-delete.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.crud.base import CRUDBase
from app.modules.work_plans.schemas.work_plan_v2_schema import (
    BulkApproveDailyPlansOut,
    DailyPlanCreateIn,
    DailyPlanOut,
    DailyPlanUpdateIn,
    DivisionOptionOut,
    OfficeSiteOptionOut,
    PlanItemCreateIn,
    PlanItemOut,
    PlanItemUpdateIn,
    ProjectPhaseSummaryOut,
    ProjectScheduleOut,
    TeamMemberOptionOut,
    TeamOptionOut,
    ToolOptionOut,
    VehicleOptionOut,
    WeeklyCalendarMatrixOut,
    WeeklyMatrixDayOut,
    WeeklyPlanCreateIn,
    WeeklyPlanDetailOut,
    WeeklyPlanListOut,
    WeeklyPlanUpdateIn,
    WorkCompletionOptionOut,
    WorkPlanFormOptionsV2Out,
    WorkTypeOptionOut,
)

INDONESIAN_DAYS = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu",
}


class CRUDWorkPlanV2(CRUDBase):
    """CRUD untuk mengelola Rencana Kerja V2 secara terintegrasi (Daily-First Architecture)."""

    async def get_form_options_v2(self) -> WorkPlanFormOptionsV2Out:
        """Mengambil data master referensi untuk dropdown form rencana kerja V2."""
        # 1. Divisi
        div_rows = await self.fetchall(
            """
            SELECT division_id, name
            FROM division
            WHERE delete_at IS NULL
            ORDER BY name ASC
            """
        )
        divisions = [DivisionOptionOut(division_id=r.division_id, name=r.name) for r in div_rows]

        # 2. Tim beserta Ketua
        team_rows = await self.fetchall(
            """
            SELECT t.team_id, t.name, t.division_id, t.leader_employee_id,
                   e.full_name AS leader_name, 'Ketua Tim' AS leader_position
            FROM team t
            LEFT JOIN employee e ON e.employee_id = t.leader_employee_id AND e.delete_at IS NULL
            WHERE t.delete_at IS NULL
            ORDER BY t.name ASC
            """
        )

        # 3. Anggota Tim (Teknisi)
        member_rows = await self.fetchall(
            """
            SELECT m.team_id, m.employee_id, e.full_name, 'Teknisi Lapangan' AS position
            FROM member m
            JOIN employee e ON e.employee_id = m.employee_id AND e.delete_at IS NULL
            WHERE m.delete_at IS NULL AND m.is_active = true
            ORDER BY e.full_name ASC
            """
        )
        members_by_team: dict[UUID, list[TeamMemberOptionOut]] = {}
        for m in member_rows:
            members_by_team.setdefault(m.team_id, []).append(
                TeamMemberOptionOut(
                    employee_id=m.employee_id,
                    full_name=m.full_name,
                    position=m.position,
                )
            )

        teams = [
            TeamOptionOut(
                team_id=t.team_id,
                name=t.name,
                division_id=t.division_id,
                leader_employee_id=t.leader_employee_id,
                leader_name=t.leader_name,
                leader_position=t.leader_position,
                members=members_by_team.get(t.team_id, []),
            )
            for t in team_rows
        ]

        # 4. Work Types (Jenis Pekerjaan)
        wt_rows = await self.fetchall(
            """
            SELECT wt.work_type_id, wt.name, wt.division_id, wt.description,
                   (
                       SELECT COUNT(*)
                       FROM image_requirement ir
                       WHERE ir.work_type_id = wt.work_type_id AND ir.delete_at IS NULL
                   ) AS img_count
            FROM work_type wt
            WHERE wt.delete_at IS NULL
            ORDER BY wt.name ASC
            """
        )
        work_types = [
            WorkTypeOptionOut(
                work_type_id=r.work_type_id,
                name=r.name,
                division_id=r.division_id,
                description=r.description,
                image_requirements_count=r.img_count or 0,
            )
            for r in wt_rows
        ]

        # 5. Work Completions (Order Klien Aktif)
        wc_rows = await self.fetchall(
            """
            SELECT wc.completion_id, wc.client_name, wc.project_title, wc.order_number, wc.division_id, wc.order_status
            FROM work_completion wc
            WHERE wc.delete_at IS NULL
            ORDER BY wc.create_at DESC
            LIMIT 50
            """
        )
        work_completions = [
            WorkCompletionOptionOut(
                completion_id=r.completion_id,
                client_name=r.client_name,
                project_title=r.project_title,
                order_number=r.order_number,
                division_id=r.division_id,
                order_status=r.order_status,
            )
            for r in wc_rows
        ]

        # 6. Kantor / Titik Site Referensi
        office_rows = await self.fetchall(
            """
            SELECT o.office_id, o.name, o.address, o.latitude, o.longitude
            FROM office o
            WHERE o.delete_at IS NULL
            ORDER BY o.is_main_office DESC, o.name ASC
            """
        )
        offices = [
            OfficeSiteOptionOut(
                office_id=r.office_id,
                name=r.name,
                address=r.address,
                latitude=float(r.latitude or 0),
                longitude=float(r.longitude or 0),
                radius_m=150,
            )
            for r in office_rows
        ]

        # 7. Peralatan Kerja
        tool_rows = await self.fetchall(
            """
            SELECT t.tool_id, t.name, t.tool_code, t.division_id, t.category::text AS category
            FROM tool t
            WHERE t.delete_at IS NULL AND t.status = 'ready'
            ORDER BY t.name ASC
            """
        )
        tools = [
            ToolOptionOut(
                tool_id=r.tool_id,
                name=r.name,
                tool_code=r.tool_code,
                division_id=r.division_id,
                category=r.category,
            )
            for r in tool_rows
        ]

        # 8. Kendaraan Operasional
        vehicle_rows = await self.fetchall(
            """
            SELECT v.vehicle_id, v.name, v.number_plate, v.vehicle_type::text AS vehicle_type, v.division_id
            FROM vehicle v
            WHERE v.delete_at IS NULL AND v.status = 'ready'
            ORDER BY v.name ASC
            """
        )
        vehicles = [
            VehicleOptionOut(
                vehicle_id=r.vehicle_id,
                name=r.name,
                number_plate=r.number_plate,
                vehicle_type=r.vehicle_type,
                division_id=r.division_id,
            )
            for r in vehicle_rows
        ]

        return WorkPlanFormOptionsV2Out(
            divisions=divisions,
            teams=teams,
            work_types=work_types,
            work_completions=work_completions,
            offices=offices,
            tools=tools,
            vehicles=vehicles,
        )

    # ── WEEKLY CALENDAR MATRIX & PROJECT SCHEDULE ─────────────────

    async def get_weekly_matrix(
        self,
        start_date: date,
        end_date: date,
        division_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> WeeklyCalendarMatrixOut:
        """Mengambil matriks kalender harian (Senin - Minggu) untuk divisi & tim tertentu."""
        div_name = None
        team_name = None
        leader_name = None
        if team_id:
            t_row = await self.fetchone(
                """
                SELECT t.name AS team_name, d.division_id, d.name AS division_name,
                       e.full_name AS leader_name
                FROM team t
                JOIN division d ON d.division_id = t.division_id
                LEFT JOIN employee e ON e.employee_id = t.leader_employee_id
                WHERE t.team_id = CAST(:tid AS uuid) AND t.delete_at IS NULL
                """,
                {"tid": str(team_id)},
            )
            if t_row:
                team_name = t_row.team_name
                division_id = t_row.division_id
                div_name = t_row.division_name
                leader_name = t_row.leader_name
        elif division_id:
            d_row = await self.fetchone(
                "SELECT name FROM division WHERE division_id = CAST(:did AS uuid) AND delete_at IS NULL",
                {"did": str(division_id)},
            )
            if d_row:
                div_name = d_row.name

        daily_rows = await self.fetchall(
            """
            SELECT wpd.daily_plan_id, wpd.division_id, d.name AS division_name,
                   wpd.team_id, t.name AS team_name, wpd.work_date,
                   wpd.site_name, wpd.site_lat, wpd.site_lng,
                   wpd.attendance_radius_m, wpd.clock_in_time, wpd.clock_out_time,
                   wpd.status, wpd.created_by_id, ce.full_name AS created_by_name,
                   wpd.approved_by_pm_id, pe.full_name AS approved_by_pm_name,
                   wpd.approved_at, wpd.rejection_reason, wpd.create_at, wpd.update_at
            FROM work_plan_daily wpd
            JOIN division d ON d.division_id = wpd.division_id
            JOIN team t ON t.team_id = wpd.team_id
            LEFT JOIN employee ce ON ce.employee_id = wpd.created_by_id
            LEFT JOIN employee pe ON pe.employee_id = wpd.approved_by_pm_id
            WHERE wpd.delete_at IS NULL
              AND wpd.work_date >= CAST(:start_date AS date)
              AND wpd.work_date <= CAST(:end_date AS date)
              AND (CAST(:div_id AS uuid) IS NULL OR wpd.division_id = CAST(:div_id AS uuid))
              AND (CAST(:team_id AS uuid) IS NULL OR wpd.team_id = CAST(:team_id AS uuid))
            ORDER BY wpd.work_date ASC
            """,
            {
                "start_date": start_date,
                "end_date": end_date,
                "div_id": str(division_id) if division_id else None,
                "team_id": str(team_id) if team_id else None,
            },
        )

        daily_ids = [r.daily_plan_id for r in daily_rows]
        items_by_day: dict[UUID, list[PlanItemOut]] = {}

        if daily_ids:
            item_rows = await self.fetchall(
                """
                SELECT wpi.item_id, wpi.daily_plan_id, wpi.work_type_id, wt.name AS work_type_name,
                       wpi.title, wpi.task_phase, wpi.is_main_deliverable, wpi.depends_on_item_id,
                       wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                       wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                       wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                       wpi.delay_reason, wpi.realization_photos_json,
                       wpi.completion_id, wc.client_name, wc.project_title, wc.order_number,
                       wpi.start_time, wpi.end_time, wpi.location_name,
                       wpi.site_lat, wpi.site_lng, wpi.assigned_employee_ids,
                       wpi.create_at, wpi.update_at
                FROM work_plan_item wpi
                JOIN work_type wt ON wt.work_type_id = wpi.work_type_id
                LEFT JOIN work_completion wc ON wc.completion_id = wpi.completion_id
                WHERE wpi.daily_plan_id = ANY(CAST(:day_ids AS uuid[])) AND wpi.delete_at IS NULL
                ORDER BY wpi.start_time ASC NULLS LAST, wpi.create_at ASC
                """,
                {"day_ids": [str(i) for i in daily_ids]},
            )
            for it in item_rows:
                assigned = it.assigned_employee_ids or []
                if isinstance(assigned, str):
                    try:
                        assigned = json.loads(assigned)
                    except (json.JSONDecodeError, TypeError):
                        assigned = []
                assigned_uuids = [UUID(str(uid)) for uid in assigned]

                items_by_day.setdefault(it.daily_plan_id, []).append(
                    PlanItemOut(
                        item_id=it.item_id,
                        daily_plan_id=it.daily_plan_id,
                        weekly_plan_id=None,
                        work_type_id=it.work_type_id,
                        work_type_name=it.work_type_name,
                        title=it.title,
                        task_phase=it.task_phase or "MAIN_INSTALLATION",
                        is_main_deliverable=bool(it.is_main_deliverable),
                        depends_on_item_id=it.depends_on_item_id,
                        target_qty=it.target_qty,
                        completed_qty=it.completed_qty,
                        progress_percent=it.progress_percent,
                        status=it.status,
                        rollover_approval_status=it.rollover_approval_status,
                        approved_by_pm_id=it.approved_by_pm_id,
                        origin_item_id=it.origin_item_id,
                        shifted_to_daily_id=it.shifted_to_daily_id,
                        allocated_to_weekly_id=None,
                        delay_reason=it.delay_reason,
                        realization_photos_json=it.realization_photos_json or [],
                        completion_id=it.completion_id,
                        client_name=it.client_name,
                        project_title=it.project_title,
                        order_number=it.order_number,
                        start_time=it.start_time,
                        end_time=it.end_time,
                        location_name=it.location_name,
                        site_lat=it.site_lat,
                        site_lng=it.site_lng,
                        assigned_employee_ids=assigned_uuids,
                        create_at=it.create_at,
                        update_at=it.update_at,
                    )
                )

        daily_by_date = {r.work_date: r for r in daily_rows}
        matrix_days: list[WeeklyMatrixDayOut] = []
        curr_d = start_date
        total_items_count = 0
        all_approved = bool(daily_rows)

        while curr_d <= end_date:
            d_rec = daily_by_date.get(curr_d)
            day_name = INDONESIAN_DAYS.get(curr_d.weekday(), "")
            if d_rec:
                d_items = items_by_day.get(d_rec.daily_plan_id, [])
                total_items_count += len(d_items)
                tot_t = sum(it.target_qty for it in d_items)
                tot_c = sum(it.completed_qty for it in d_items)
                pct = (tot_c / tot_t * Decimal("100.00")) if tot_t > 0 else Decimal("0.00")
                if d_rec.status != "APPROVED":
                    all_approved = False

                matrix_days.append(
                    WeeklyMatrixDayOut(
                        date=curr_d,
                        day_name=day_name,
                        daily_plan_id=d_rec.daily_plan_id,
                        division_id=d_rec.division_id,
                        team_id=d_rec.team_id,
                        site_name=d_rec.site_name,
                        site_lat=d_rec.site_lat,
                        site_lng=d_rec.site_lng,
                        status=d_rec.status,
                        approved_by_pm_id=d_rec.approved_by_pm_id,
                        approved_by_pm_name=d_rec.approved_by_pm_name,
                        approved_at=d_rec.approved_at,
                        is_holiday=(d_rec.status == "HOLIDAY"),
                        items=d_items,
                        total_target_qty=tot_t,
                        total_completed_qty=tot_c,
                        progress_percent=round(pct, 2),
                    )
                )
            else:
                matrix_days.append(
                    WeeklyMatrixDayOut(
                        date=curr_d,
                        day_name=day_name,
                        daily_plan_id=None,
                        division_id=division_id,
                        team_id=team_id,
                        site_name=None,
                        site_lat=None,
                        site_lng=None,
                        status=None,
                        is_holiday=False,
                        items=[],
                        total_target_qty=Decimal("0.00"),
                        total_completed_qty=Decimal("0.00"),
                        progress_percent=Decimal("0.00"),
                    )
                )
            curr_d += timedelta(days=1)

        return WeeklyCalendarMatrixOut(
            start_date=start_date,
            end_date=end_date,
            division_id=division_id,
            division_name=div_name,
            team_id=team_id,
            team_name=team_name,
            leader_name=leader_name,
            total_days=len(matrix_days),
            scheduled_days=len(daily_rows),
            total_items=total_items_count,
            all_approved=all_approved,
            days=matrix_days,
        )

    async def bulk_approve_days(
        self,
        pm_employee_id: UUID,
        start_date: date,
        end_date: date,
        team_id: UUID,
    ) -> BulkApproveDailyPlansOut:
        """PM menyetujui seluruh hari kerja tim dalam rentang tanggal tertentu sekaligus."""
        res = await self.execute(
            """
            UPDATE work_plan_daily
            SET status = 'APPROVED',
                approved_by_pm_id = CAST(:pm_id AS uuid),
                approved_at = NOW(),
                update_at = NOW()
            WHERE team_id = CAST(:tid AS uuid)
              AND work_date >= CAST(:start_date AS date)
              AND work_date <= CAST(:end_date AS date)
              AND status IN ('SUBMITTED', 'ONGOING', 'SCHEDULED')
              AND delete_at IS NULL
            """,
            {
                "pm_id": str(pm_employee_id),
                "tid": str(team_id),
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        count = res.rowcount
        return BulkApproveDailyPlansOut(
            success=True,
            approved_count=count,
            message=f"{count} hari kerja berhasil disetujui oleh Project Manager.",
        )

    async def get_project_schedule(self, completion_id: UUID) -> ProjectScheduleOut | None:
        """Mengambil linimasa proyek multi-minggu (CCTV Site A, B dsb) dengan agregasi per fase pekerjaan."""
        comp = await self.fetchone(
            """
            SELECT wc.completion_id, wc.client_name, wc.project_title, wc.order_number,
                   wc.division_id, d.name AS division_name, wc.order_status,
                   wc.start_work_date, wc.end_work_date, wc.total_target_unit
            FROM work_completion wc
            LEFT JOIN division d ON d.division_id = wc.division_id
            WHERE wc.completion_id = CAST(:cid AS uuid) AND wc.delete_at IS NULL
            """,
            {"cid": str(completion_id)},
        )
        if not comp:
            return None

        rows = await self.fetchall(
            """
            SELECT wpi.item_id, wpi.daily_plan_id, wpd.work_date, wpi.work_type_id, wt.name AS work_type_name,
                   wpi.title, wpi.task_phase, wpi.is_main_deliverable, wpi.depends_on_item_id,
                   wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                   wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                   wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                   wpi.delay_reason, wpi.realization_photos_json,
                   wpi.completion_id,
                   wpi.start_time, wpi.end_time, wpi.location_name,
                   wpi.site_lat, wpi.site_lng, wpi.assigned_employee_ids,
                   wpi.create_at, wpi.update_at
            FROM work_plan_item wpi
            JOIN work_plan_daily wpd ON wpd.daily_plan_id = wpi.daily_plan_id
            JOIN work_type wt ON wt.work_type_id = wpi.work_type_id
            WHERE wpi.completion_id = CAST(:cid AS uuid) AND wpi.delete_at IS NULL
            ORDER BY wpd.work_date ASC, wpi.start_time ASC NULLS LAST, wpi.create_at ASC
            """,
            {"cid": str(completion_id)},
        )

        timeline_items: list[PlanItemOut] = []
        phase_map: dict[str, dict[str, Any]] = {}
        phase_labels = {
            "SURVEY": "Tahap 1: Survei Lapangan & Identifikasi Jalur",
            "PREPARATION": "Tahap 2: Persiapan Skafolding & Galian",
            "MAIN_INSTALLATION": "Tahap 3: Instalasi Fisik Unit",
            "TESTING_COMMISSIONING": "Tahap 4: Uji Coba & BAST (Completion)",
        }

        tot_deliv_target = Decimal("0.00")
        tot_deliv_comp = Decimal("0.00")

        for r in rows:
            assigned = r.assigned_employee_ids or []
            if isinstance(assigned, str):
                try:
                    assigned = json.loads(assigned)
                except (json.JSONDecodeError, TypeError):
                    assigned = []
            assigned_uuids = [UUID(str(uid)) for uid in assigned]

            item_out = PlanItemOut(
                item_id=r.item_id,
                daily_plan_id=r.daily_plan_id,
                weekly_plan_id=None,
                work_type_id=r.work_type_id,
                work_type_name=r.work_type_name,
                title=r.title,
                task_phase=r.task_phase or "MAIN_INSTALLATION",
                is_main_deliverable=bool(r.is_main_deliverable),
                depends_on_item_id=r.depends_on_item_id,
                target_qty=r.target_qty,
                completed_qty=r.completed_qty,
                progress_percent=r.progress_percent,
                status=r.status,
                rollover_approval_status=r.rollover_approval_status,
                approved_by_pm_id=r.approved_by_pm_id,
                origin_item_id=r.origin_item_id,
                shifted_to_daily_id=r.shifted_to_daily_id,
                allocated_to_weekly_id=None,
                delay_reason=r.delay_reason,
                realization_photos_json=r.realization_photos_json or [],
                completion_id=r.completion_id,
                client_name=comp.client_name,
                project_title=comp.project_title,
                order_number=comp.order_number,
                start_time=r.start_time,
                end_time=r.end_time,
                location_name=r.location_name,
                site_lat=r.site_lat,
                site_lng=r.site_lng,
                assigned_employee_ids=assigned_uuids,
                create_at=r.create_at,
                update_at=r.update_at,
            )
            timeline_items.append(item_out)

            phase = r.task_phase or "MAIN_INSTALLATION"
            if phase not in phase_map:
                phase_map[phase] = {
                    "task_phase": phase,
                    "phase_label": phase_labels.get(phase, phase),
                    "total_target_qty": Decimal("0.00"),
                    "total_completed_qty": Decimal("0.00"),
                    "items_count": 0,
                    "is_completed": True,
                }

            p_data = phase_map[phase]
            p_data["total_target_qty"] += r.target_qty
            p_data["total_completed_qty"] += r.completed_qty
            p_data["items_count"] += 1
            if r.status != "DONE":
                p_data["is_completed"] = False

            if bool(r.is_main_deliverable):
                tot_deliv_target += r.target_qty
                tot_deliv_comp += r.completed_qty

        phases_out: list[ProjectPhaseSummaryOut] = []
        for p_key in ["SURVEY", "PREPARATION", "MAIN_INSTALLATION", "TESTING_COMMISSIONING"]:
            if p_key in phase_map:
                p = phase_map[p_key]
                pct = (
                    (p["total_completed_qty"] / p["total_target_qty"] * Decimal("100.00"))
                    if p["total_target_qty"] > 0
                    else Decimal("0.00")
                )
                phases_out.append(
                    ProjectPhaseSummaryOut(
                        task_phase=p["task_phase"],
                        phase_label=p["phase_label"],
                        total_target_qty=p["total_target_qty"],
                        total_completed_qty=p["total_completed_qty"],
                        progress_percent=round(pct, 2),
                        is_completed=p["is_completed"],
                        items_count=p["items_count"],
                    )
                )

        deliv_pct = (
            (tot_deliv_comp / tot_deliv_target * Decimal("100.00"))
            if tot_deliv_target > 0
            else Decimal("0.00")
        )
        is_ready = bool(tot_deliv_target > 0 and tot_deliv_comp >= tot_deliv_target)

        min_d = timeline_items[0].create_at.date() if timeline_items and timeline_items[0].create_at else None
        max_d = timeline_items[-1].create_at.date() if timeline_items and timeline_items[-1].create_at else None

        return ProjectScheduleOut(
            completion_id=comp.completion_id,
            client_name=comp.client_name,
            project_title=comp.project_title,
            order_number=comp.order_number,
            division_id=comp.division_id,
            division_name=comp.division_name,
            order_status=comp.order_status,
            start_work_date=comp.start_work_date or min_d,
            end_work_date=comp.end_work_date or max_d,
            total_target_deliverables=tot_deliv_target,
            total_completed_deliverables=tot_deliv_comp,
            deliverables_progress_percent=round(deliv_pct, 2),
            is_ready_for_completion=is_ready,
            phases=phases_out,
            timeline_items=timeline_items,
        )

    # ── WEEKLY PLAN BACKWARD COMPATIBILITY ADAPTER ────────────────

    async def list_weekly_plans(
        self,
        *,
        status_filter: str | None = None,
        division_id: UUID | None = None,
        team_id: UUID | None = None,
        year: int | None = None,
        limit: int = 50,
    ) -> list[WeeklyPlanListOut]:
        """Mendaftar rencana kerja mingguan (agregasi kalender harian secara otomatis)."""
        rows = await self.fetchall(
            """
            SELECT
                wpd.division_id,
                d.name AS division_name,
                wpd.team_id,
                t.name AS team_name,
                CAST(EXTRACT(WEEK FROM wpd.work_date) AS integer) AS week_number,
                CAST(EXTRACT(YEAR FROM wpd.work_date) AS integer) AS year,
                DATE_TRUNC('week', wpd.work_date)::date AS start_date,
                (DATE_TRUNC('week', wpd.work_date) + interval '6 days')::date AS end_date,
                CASE
                    WHEN bool_and(wpd.status = 'APPROVED') THEN 'APPROVED'
                    WHEN bool_or(wpd.status = 'ONGOING') THEN 'ONGOING'
                    ELSE 'SUBMITTED'
                END AS status,
                COUNT(DISTINCT wpd.daily_plan_id) AS total_days,
                COUNT(wpi.item_id) AS total_items,
                MIN(wpd.create_at) AS create_at,
                MIN(wpd.daily_plan_id) AS first_daily_id
            FROM work_plan_daily wpd
            JOIN division d ON d.division_id = wpd.division_id
            JOIN team t ON t.team_id = wpd.team_id
            LEFT JOIN work_plan_item wpi ON wpi.daily_plan_id = wpd.daily_plan_id AND wpi.delete_at IS NULL
            WHERE wpd.delete_at IS NULL
              AND (CAST(:status AS varchar) IS NULL OR wpd.status = CAST(:status AS varchar))
              AND (CAST(:div_id AS uuid) IS NULL OR wpd.division_id = CAST(:div_id AS uuid))
              AND (CAST(:team_id AS uuid) IS NULL OR wpd.team_id = CAST(:team_id AS uuid))
              AND (CAST(:year AS smallint) IS NULL OR EXTRACT(YEAR FROM wpd.work_date) = CAST(:year AS smallint))
            GROUP BY wpd.division_id, d.name, wpd.team_id, t.name,
                     EXTRACT(YEAR FROM wpd.work_date), EXTRACT(WEEK FROM wpd.work_date),
                     DATE_TRUNC('week', wpd.work_date)
            ORDER BY start_date DESC
            LIMIT :limit
            """,
            {
                "status": status_filter,
                "div_id": str(division_id) if division_id else None,
                "team_id": str(team_id) if team_id else None,
                "year": year,
                "limit": limit,
            },
        )
        return [
            WeeklyPlanListOut(
                weekly_plan_id=r.first_daily_id,
                division_id=r.division_id,
                division_name=r.division_name,
                team_id=r.team_id,
                team_name=r.team_name,
                week_number=r.week_number,
                year=r.year,
                start_date=r.start_date,
                end_date=r.end_date,
                status=r.status,
                total_days=r.total_days or 0,
                total_items=r.total_items or 0,
                create_at=r.create_at,
            )
            for r in rows
        ]

    async def get_weekly_plan_detail(self, weekly_plan_id: UUID) -> WeeklyPlanDetailOut | None:
        """Mengambil satu rencana kerja mingguan lengkap dengan seluruh hari dan butir tugasnya."""
        first_day = await self.get_daily_plan(weekly_plan_id)
        if not first_day:
            return None

        # Ambil seluruh hari dalam minggu yang sama
        start_week = first_day.work_date - timedelta(days=first_day.work_date.weekday())
        end_week = start_week + timedelta(days=6)

        matrix = await self.get_weekly_matrix(
            start_date=start_week,
            end_date=end_week,
            division_id=first_day.division_id,
            team_id=first_day.team_id,
        )

        days_out: list[DailyPlanOut] = []
        for m_day in matrix.days:
            if m_day.daily_plan_id:
                d_detail = await self.get_daily_plan(m_day.daily_plan_id)
                if d_detail:
                    days_out.append(d_detail)

        return WeeklyPlanDetailOut(
            weekly_plan_id=first_day.daily_plan_id,
            division_id=first_day.division_id,
            division_name=first_day.division_name or "",
            team_id=first_day.team_id,
            team_name=first_day.team_name or "",
            leader_name=matrix.leader_name,
            week_number=first_day.work_date.isocalendar()[1],
            year=first_day.work_date.year,
            start_date=start_week,
            end_date=end_week,
            created_by_id=first_day.created_by_id or first_day.daily_plan_id,
            created_by_name=first_day.created_by_name,
            approved_by_pm_id=first_day.approved_by_pm_id,
            approved_by_pm_name=first_day.approved_by_pm_name,
            status=first_day.status,
            days=days_out,
            create_at=first_day.create_at,
            update_at=first_day.update_at,
        )

    async def create_weekly_plan(
        self,
        creator_employee_id: UUID,
        payload: WeeklyPlanCreateIn,
    ) -> WeeklyPlanDetailOut:
        """Membuat hari-hari kerja langsung dari payload mingguan."""
        created_days: list[DailyPlanOut] = []
        for d in payload.days:
            d.division_id = payload.division_id
            d.team_id = payload.team_id
            created_day = await self.create_daily_plan(d, creator_employee_id)
            created_days.append(created_day)

        first_id = created_days[0].daily_plan_id if created_days else UUID("00000000-0000-0000-0000-000000000000")
        detail = await self.get_weekly_plan_detail(first_id)
        assert detail is not None
        return detail

    async def update_weekly_plan(
        self,
        weekly_plan_id: UUID,
        payload: WeeklyPlanUpdateIn,
    ) -> WeeklyPlanDetailOut | None:
        """Memperbarui hari kerja."""
        return await self.get_weekly_plan_detail(weekly_plan_id)

    async def delete_weekly_plan(self, weekly_plan_id: UUID) -> bool:
        """Soft-delete hari kerja."""
        return await self.delete_daily_plan(weekly_plan_id)

    # ── DAILY PLAN CRUD ───────────────────────────────────────────

    async def get_daily_plan(self, daily_plan_id: UUID) -> DailyPlanOut | None:
        """Mengambil satu hari kerja beserta slot tugasnya."""
        d = await self.fetchone(
            """
            SELECT wpd.daily_plan_id, wpd.division_id, d.name AS division_name,
                   wpd.team_id, t.name AS team_name, wpd.work_date, wpd.site_name,
                   wpd.site_lat, wpd.site_lng, wpd.attendance_radius_m, wpd.clock_in_time,
                   wpd.clock_out_time, wpd.status, wpd.created_by_id, ce.full_name AS created_by_name,
                   wpd.approved_by_pm_id, pe.full_name AS approved_by_pm_name,
                   wpd.approved_at, wpd.rejection_reason, wpd.create_at, wpd.update_at
            FROM work_plan_daily wpd
            JOIN division d ON d.division_id = wpd.division_id
            JOIN team t ON t.team_id = wpd.team_id
            LEFT JOIN employee ce ON ce.employee_id = wpd.created_by_id
            LEFT JOIN employee pe ON pe.employee_id = wpd.approved_by_pm_id
            WHERE wpd.daily_plan_id = CAST(:day AS uuid) AND wpd.delete_at IS NULL
            """,
            {"day": str(daily_plan_id)},
        )
        if not d:
            return None

        # Ambil items untuk hari ini
        item_rows = await self.fetchall(
            """
            SELECT wpi.item_id, wpi.daily_plan_id,
                   wpi.work_type_id, wt.name AS work_type_name,
                   wpi.title, wpi.task_phase, wpi.is_main_deliverable, wpi.depends_on_item_id,
                   wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                   wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                   wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                   wpi.delay_reason, wpi.realization_photos_json,
                   wpi.completion_id, wc.client_name, wc.project_title, wc.order_number,
                   wpi.start_time, wpi.end_time, wpi.location_name,
                   wpi.site_lat, wpi.site_lng, wpi.assigned_employee_ids,
                   wpi.create_at, wpi.update_at
            FROM work_plan_item wpi
            JOIN work_type wt ON wt.work_type_id = wpi.work_type_id
            LEFT JOIN work_completion wc ON wc.completion_id = wpi.completion_id
            WHERE wpi.daily_plan_id = CAST(:day AS uuid) AND wpi.delete_at IS NULL
            ORDER BY wpi.start_time ASC NULLS LAST, wpi.create_at ASC
            """,
            {"day": str(daily_plan_id)},
        )

        items_out = []
        for it in item_rows:
            assigned = it.assigned_employee_ids or []
            if isinstance(assigned, str):
                try:
                    assigned = json.loads(assigned)
                except (json.JSONDecodeError, TypeError):
                    assigned = []
            assigned_uuids = [UUID(str(uid)) for uid in assigned]

            items_out.append(
                PlanItemOut(
                    item_id=it.item_id,
                    daily_plan_id=it.daily_plan_id,
                    weekly_plan_id=None,
                    work_type_id=it.work_type_id,
                    work_type_name=it.work_type_name,
                    title=it.title,
                    task_phase=it.task_phase or "MAIN_INSTALLATION",
                    is_main_deliverable=bool(it.is_main_deliverable),
                    depends_on_item_id=it.depends_on_item_id,
                    target_qty=it.target_qty,
                    completed_qty=it.completed_qty,
                    progress_percent=it.progress_percent,
                    status=it.status,
                    rollover_approval_status=it.rollover_approval_status,
                    approved_by_pm_id=it.approved_by_pm_id,
                    origin_item_id=it.origin_item_id,
                    shifted_to_daily_id=it.shifted_to_daily_id,
                    allocated_to_weekly_id=None,
                    delay_reason=it.delay_reason,
                    realization_photos_json=it.realization_photos_json or [],
                    completion_id=it.completion_id,
                    client_name=it.client_name,
                    project_title=it.project_title,
                    order_number=it.order_number,
                    start_time=it.start_time,
                    end_time=it.end_time,
                    location_name=it.location_name,
                    site_lat=it.site_lat,
                    site_lng=it.site_lng,
                    assigned_employee_ids=assigned_uuids,
                    create_at=it.create_at,
                    update_at=it.update_at,
                )
            )

        return DailyPlanOut(
            daily_plan_id=d.daily_plan_id,
            division_id=d.division_id,
            division_name=d.division_name,
            team_id=d.team_id,
            team_name=d.team_name,
            weekly_plan_id=None,
            work_date=d.work_date,
            site_name=d.site_name,
            site_lat=d.site_lat,
            site_lng=d.site_lng,
            attendance_radius_m=d.attendance_radius_m,
            clock_in_time=d.clock_in_time,
            clock_out_time=d.clock_out_time,
            status=d.status,
            created_by_id=d.created_by_id,
            created_by_name=d.created_by_name,
            approved_by_pm_id=d.approved_by_pm_id,
            approved_by_pm_name=d.approved_by_pm_name,
            approved_at=d.approved_at,
            rejection_reason=d.rejection_reason,
            is_holiday=(d.status == "HOLIDAY"),
            items=items_out,
            create_at=d.create_at,
            update_at=d.update_at,
        )

    async def create_daily_plan(
        self,
        payload: DailyPlanCreateIn,
        creator_employee_id: UUID | None = None,
    ) -> DailyPlanOut:
        """Membuat hari kerja baru langsung sebagai entitas utama."""
        cid = creator_employee_id or await self.get_creator_employee_id(payload.division_id)
        res = await self.fetchone(
            """
            INSERT INTO work_plan_daily (
                division_id, team_id, work_date, site_name, site_lat, site_lng,
                attendance_radius_m, clock_in_time, clock_out_time, status, created_by_id
            )
            VALUES (
                CAST(:div_id AS uuid),
                CAST(:team_id AS uuid),
                CAST(:work_date AS date),
                :site_name,
                CAST(:site_lat AS numeric),
                CAST(:site_lng AS numeric),
                CAST(:radius AS integer),
                CAST(:clock_in AS time),
                CAST(:clock_out AS time),
                CAST(:status AS varchar),
                CAST(:creator_id AS uuid)
            )
            RETURNING daily_plan_id
            """,
            {
                "div_id": str(payload.division_id),
                "team_id": str(payload.team_id),
                "work_date": payload.work_date,
                "site_name": payload.site_name,
                "site_lat": payload.site_lat,
                "site_lng": payload.site_lng,
                "radius": payload.attendance_radius_m,
                "clock_in": payload.clock_in_time,
                "clock_out": payload.clock_out_time,
                "status": "HOLIDAY" if payload.is_holiday else payload.status,
                "creator_id": str(cid),
            },
        )
        daily_plan_id = res.daily_plan_id

        # Simpan items jika disertakan
        for it in payload.items:
            it.daily_plan_id = daily_plan_id
            await self.create_plan_item(it)

        detail = await self.get_daily_plan(daily_plan_id)
        assert detail is not None
        return detail

    async def update_daily_plan(
        self,
        daily_plan_id: UUID,
        payload: DailyPlanUpdateIn,
    ) -> DailyPlanOut | None:
        """Memperbarui hari kerja."""
        await self.execute(
            """
            UPDATE work_plan_daily
            SET division_id = COALESCE(CAST(:div_id AS uuid), division_id),
                team_id = COALESCE(CAST(:team_id AS uuid), team_id),
                work_date = COALESCE(CAST(:work_date AS date), work_date),
                site_name = COALESCE(:site_name, site_name),
                site_lat = COALESCE(CAST(:site_lat AS numeric), site_lat),
                site_lng = COALESCE(CAST(:site_lng AS numeric), site_lng),
                attendance_radius_m = COALESCE(CAST(:radius AS integer), attendance_radius_m),
                clock_in_time = COALESCE(CAST(:clock_in AS time), clock_in_time),
                clock_out_time = COALESCE(CAST(:clock_out AS time), clock_out_time),
                status = COALESCE(CAST(:status AS varchar), status),
                rejection_reason = COALESCE(:rej_reason, rejection_reason),
                update_at = now()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {
                "day": str(daily_plan_id),
                "div_id": str(payload.division_id) if payload.division_id else None,
                "team_id": str(payload.team_id) if payload.team_id else None,
                "work_date": payload.work_date,
                "site_name": payload.site_name,
                "site_lat": payload.site_lat,
                "site_lng": payload.site_lng,
                "radius": payload.attendance_radius_m,
                "clock_in": payload.clock_in_time,
                "clock_out": payload.clock_out_time,
                "status": "HOLIDAY" if payload.is_holiday else payload.status,
                "rej_reason": payload.rejection_reason,
            },
        )
        return await self.get_daily_plan(daily_plan_id)

    async def delete_daily_plan(self, daily_plan_id: UUID) -> bool:
        """Soft delete hari kerja dan tugas-tugas di dalamnya."""
        await self.execute(
            """
            UPDATE work_plan_item
            SET delete_at = now()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {"day": str(daily_plan_id)},
        )
        res = await self.execute(
            """
            UPDATE work_plan_daily
            SET delete_at = now()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {"day": str(daily_plan_id)},
        )
        return bool(res.rowcount > 0)

    # ── PLAN ITEM CRUD ───────────────────────────────────────────

    async def get_plan_item(self, item_id: UUID) -> PlanItemOut | None:
        """Mengambil satu butir tugas secara detail."""
        it = await self.fetchone(
            """
            SELECT wpi.item_id, wpi.daily_plan_id,
                   wpi.work_type_id, wt.name AS work_type_name,
                   wpi.title, wpi.task_phase, wpi.is_main_deliverable, wpi.depends_on_item_id,
                   wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                   wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                   wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                   wpi.delay_reason, wpi.realization_photos_json,
                   wpi.completion_id, wc.client_name, wc.project_title, wc.order_number,
                   wpi.start_time, wpi.end_time, wpi.location_name,
                   wpi.site_lat, wpi.site_lng, wpi.assigned_employee_ids,
                   wpi.create_at, wpi.update_at
            FROM work_plan_item wpi
            JOIN work_type wt ON wt.work_type_id = wpi.work_type_id
            LEFT JOIN work_completion wc ON wc.completion_id = wpi.completion_id
            WHERE wpi.item_id = CAST(:item AS uuid) AND wpi.delete_at IS NULL
            """,
            {"item": str(item_id)},
        )
        if not it:
            return None

        assigned = it.assigned_employee_ids or []
        if isinstance(assigned, str):
            try:
                assigned = json.loads(assigned)
            except (json.JSONDecodeError, TypeError):
                assigned = []
        assigned_uuids = [UUID(str(uid)) for uid in assigned]

        return PlanItemOut(
            item_id=it.item_id,
            daily_plan_id=it.daily_plan_id,
            weekly_plan_id=None,
            work_type_id=it.work_type_id,
            work_type_name=it.work_type_name,
            title=it.title,
            task_phase=it.task_phase or "MAIN_INSTALLATION",
            is_main_deliverable=bool(it.is_main_deliverable),
            depends_on_item_id=it.depends_on_item_id,
            target_qty=it.target_qty,
            completed_qty=it.completed_qty,
            progress_percent=it.progress_percent,
            status=it.status,
            rollover_approval_status=it.rollover_approval_status,
            approved_by_pm_id=it.approved_by_pm_id,
            origin_item_id=it.origin_item_id,
            shifted_to_daily_id=it.shifted_to_daily_id,
            allocated_to_weekly_id=None,
            delay_reason=it.delay_reason,
            realization_photos_json=it.realization_photos_json or [],
            completion_id=it.completion_id,
            client_name=it.client_name,
            project_title=it.project_title,
            order_number=it.order_number,
            start_time=it.start_time,
            end_time=it.end_time,
            location_name=it.location_name,
            site_lat=it.site_lat,
            site_lng=it.site_lng,
            assigned_employee_ids=assigned_uuids,
            create_at=it.create_at,
            update_at=it.update_at,
        )

    async def create_plan_item(self, payload: PlanItemCreateIn) -> PlanItemOut:
        """Membuat butir tugas slot kerja baru."""
        assigned_json = json.dumps([str(uid) for uid in payload.assigned_employee_ids])
        photos_json = json.dumps(payload.realization_photos_json or [])

        res = await self.fetchone(
            """
            INSERT INTO work_plan_item (
                daily_plan_id,
                work_type_id,
                title,
                task_phase,
                is_main_deliverable,
                depends_on_item_id,
                target_qty,
                completed_qty,
                progress_percent,
                status,
                rollover_approval_status,
                completion_id,
                start_time,
                end_time,
                location_name,
                site_lat,
                site_lng,
                assigned_employee_ids,
                realization_photos_json
            )
            VALUES (
                CAST(:day_id AS uuid),
                CAST(:wt_id AS uuid),
                :title,
                CAST(:task_phase AS varchar),
                CAST(:is_deliverable AS boolean),
                CAST(:depends_on_id AS uuid),
                CAST(:target_qty AS numeric),
                CAST(:comp_qty AS numeric),
                CAST(:prog AS numeric),
                CAST(:status AS varchar),
                CAST(:rollover_status AS rollover_approval_enum),
                CAST(:completion_id AS uuid),
                CAST(:start_time AS time),
                CAST(:end_time AS time),
                :loc_name,
                CAST(:site_lat AS numeric),
                CAST(:site_lng AS numeric),
                CAST(:assigned AS jsonb),
                CAST(:photos AS jsonb)
            )
            RETURNING item_id
            """,
            {
                "day_id": str(payload.daily_plan_id),
                "wt_id": str(payload.work_type_id),
                "title": payload.title,
                "task_phase": payload.task_phase or "MAIN_INSTALLATION",
                "is_deliverable": payload.is_main_deliverable,
                "depends_on_id": str(payload.depends_on_item_id) if payload.depends_on_item_id else None,
                "target_qty": payload.target_qty,
                "comp_qty": payload.completed_qty,
                "prog": payload.progress_percent,
                "status": payload.status,
                "rollover_status": payload.rollover_approval_status or "NONE",
                "completion_id": str(payload.completion_id) if payload.completion_id else None,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "loc_name": payload.location_name,
                "site_lat": payload.site_lat,
                "site_lng": payload.site_lng,
                "assigned": assigned_json,
                "photos": photos_json,
            },
        )
        item_id = res.item_id
        detail = await self.get_plan_item(item_id)
        assert detail is not None
        return detail

    async def update_plan_item(
        self,
        item_id: UUID,
        payload: PlanItemUpdateIn,
    ) -> PlanItemOut | None:
        """Memperbarui butir tugas."""
        assigned_json = (
            json.dumps([str(uid) for uid in payload.assigned_employee_ids])
            if payload.assigned_employee_ids is not None
            else None
        )
        photos_json = (
            json.dumps(payload.realization_photos_json)
            if payload.realization_photos_json is not None
            else None
        )

        await self.execute(
            """
            UPDATE work_plan_item
            SET title = COALESCE(:title, title),
                task_phase = COALESCE(CAST(:task_phase AS varchar), task_phase),
                is_main_deliverable = COALESCE(CAST(:is_deliverable AS boolean), is_main_deliverable),
                depends_on_item_id = CASE
                    WHEN CAST(:dep_set AS boolean) THEN CAST(:depends_on_id AS uuid)
                    ELSE depends_on_item_id
                END,
                work_type_id = COALESCE(CAST(:wt_id AS uuid), work_type_id),
                completion_id = CASE
                    WHEN CAST(:comp_id_set AS boolean) THEN CAST(:comp_id AS uuid)
                    ELSE completion_id
                END,
                target_qty = COALESCE(CAST(:target_qty AS numeric), target_qty),
                completed_qty = COALESCE(CAST(:comp_qty AS numeric), completed_qty),
                progress_percent = COALESCE(CAST(:prog AS numeric), progress_percent),
                status = COALESCE(CAST(:status AS varchar), status),
                rollover_approval_status = COALESCE(
                    CAST(:rollover_status AS rollover_approval_enum),
                    rollover_approval_status
                ),
                delay_reason = COALESCE(:delay_reason, delay_reason),
                start_time = COALESCE(CAST(:start_time AS time), start_time),
                end_time = COALESCE(CAST(:end_time AS time), end_time),
                location_name = COALESCE(:loc_name, location_name),
                site_lat = COALESCE(CAST(:site_lat AS numeric), site_lat),
                site_lng = COALESCE(CAST(:site_lng AS numeric), site_lng),
                assigned_employee_ids = COALESCE(CAST(:assigned AS jsonb), assigned_employee_ids),
                realization_photos_json = COALESCE(CAST(:photos AS jsonb), realization_photos_json),
                update_at = now()
            WHERE item_id = CAST(:item AS uuid) AND delete_at IS NULL
            """,
            {
                "item": str(item_id),
                "title": payload.title,
                "task_phase": payload.task_phase,
                "is_deliverable": payload.is_main_deliverable,
                "dep_set": payload.depends_on_item_id is not None,
                "depends_on_id": str(payload.depends_on_item_id) if payload.depends_on_item_id else None,
                "wt_id": str(payload.work_type_id) if payload.work_type_id else None,
                "comp_id_set": payload.completion_id is not None,
                "comp_id": str(payload.completion_id) if payload.completion_id else None,
                "target_qty": payload.target_qty,
                "comp_qty": payload.completed_qty,
                "prog": payload.progress_percent,
                "status": payload.status,
                "rollover_status": payload.rollover_approval_status,
                "delay_reason": payload.delay_reason,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "loc_name": payload.location_name,
                "site_lat": payload.site_lat,
                "site_lng": payload.site_lng,
                "assigned": assigned_json,
                "photos": photos_json,
            },
        )
        return await self.get_plan_item(item_id)

    async def delete_plan_item(self, item_id: UUID) -> bool:
        """Soft delete butir tugas."""
        res = await self.execute(
            """
            UPDATE work_plan_item
            SET delete_at = now()
            WHERE item_id = CAST(:item AS uuid) AND delete_at IS NULL
            """,
            {"item": str(item_id)},
        )
        return bool(res.rowcount > 0)

    async def get_creator_employee_id(self, user_id: UUID | str) -> UUID:
        """Mendapatkan employee_id dari pengguna atau fallback ke karyawan aktif pertama."""
        row = await self.fetchone(
            """
            SELECT e.employee_id
            FROM users u
            JOIN employee e ON e.employee_id = u.employee_id
            WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL AND e.delete_at IS NULL
            """,
            {"uid": str(user_id)},
        )
        if row and row.employee_id:
            return row.employee_id

        # Fallback untuk user admin atau session tanpa tautan langsung
        row_emp = await self.fetchone(
            """
            SELECT employee_id FROM employee WHERE delete_at IS NULL ORDER BY create_at ASC LIMIT 1
            """
        )
        if row_emp and row_emp.employee_id:
            return row_emp.employee_id
        raise ValueError("Tidak ditemukan data karyawan aktif untuk pencatatan pembuat rencana kerja.")

