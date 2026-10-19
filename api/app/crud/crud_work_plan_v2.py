"""
api/app/crud/crud_work_plan_v2.py
Akses data database statis ANSI SQL untuk Work Plan V2:
- Form Options V2
- CRUD work_plan_weekly
- CRUD work_plan_daily
- CRUD work_plan_item
Mengikuti aturan SQL statis, parameter binding, CAST(:x AS type), dan soft-delete.
"""

from __future__ import annotations

import json
from uuid import UUID

from app.crud.base import CRUDBase
from app.modules.work_plans.schemas.work_plan_v2_schema import (
    DailyPlanCreateIn,
    DailyPlanOut,
    DailyPlanUpdateIn,
    DivisionOptionOut,
    OfficeSiteOptionOut,
    PlanItemCreateIn,
    PlanItemOut,
    PlanItemUpdateIn,
    TeamMemberOptionOut,
    TeamOptionOut,
    ToolOptionOut,
    VehicleOptionOut,
    WeeklyPlanCreateIn,
    WeeklyPlanDetailOut,
    WeeklyPlanListOut,
    WeeklyPlanUpdateIn,
    WorkCompletionOptionOut,
    WorkPlanFormOptionsV2Out,
    WorkTypeOptionOut,
)


class CRUDWorkPlanV2(CRUDBase):
    """CRUD untuk mengelola Rencana Kerja V2 secara terintegrasi."""

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

    # ── WEEKLY PLAN CRUD ──────────────────────────────────────────

    async def list_weekly_plans(
        self,
        *,
        status_filter: str | None = None,
        division_id: UUID | None = None,
        team_id: UUID | None = None,
        year: int | None = None,
        limit: int = 50,
    ) -> list[WeeklyPlanListOut]:
        """Mendaftar rencana kerja mingguan dengan statistik jumlah hari dan item."""
        rows = await self.fetchall(
            """
            SELECT wp.weekly_plan_id, wp.division_id, d.name AS division_name,
                   wp.team_id, t.name AS team_name, wp.week_number, wp.year,
                   wp.start_date, wp.end_date, wp.status, wp.create_at,
                   (
                       SELECT count(*) FROM work_plan_daily wpd
                       WHERE wpd.weekly_plan_id = wp.weekly_plan_id AND wpd.delete_at IS NULL
                   ) AS total_days,
                   (
                       SELECT count(*) FROM work_plan_item wpi
                       WHERE wpi.weekly_plan_id = wp.weekly_plan_id AND wpi.delete_at IS NULL
                   ) AS total_items
            FROM work_plan_weekly wp

            JOIN division d ON d.division_id = wp.division_id
            JOIN team t ON t.team_id = wp.team_id
            WHERE wp.delete_at IS NULL
              AND (CAST(:status AS varchar) IS NULL OR wp.status = CAST(:status AS varchar))
              AND (CAST(:div_id AS uuid) IS NULL OR wp.division_id = CAST(:div_id AS uuid))
              AND (CAST(:team_id AS uuid) IS NULL OR wp.team_id = CAST(:team_id AS uuid))
              AND (CAST(:year AS smallint) IS NULL OR wp.year = CAST(:year AS smallint))
            ORDER BY wp.year DESC, wp.week_number DESC, wp.create_at DESC
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
                weekly_plan_id=r.weekly_plan_id,
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
        wp = await self.fetchone(
            """
            SELECT wp.weekly_plan_id, wp.division_id, d.name AS division_name,
                   wp.team_id, t.name AS team_name, t.leader_employee_id,
                   le.full_name AS leader_name,
                   wp.week_number, wp.year, wp.start_date, wp.end_date,
                   wp.created_by_id, ce.full_name AS created_by_name,
                   wp.approved_by_pm_id, pe.full_name AS approved_by_pm_name,
                   wp.status, wp.create_at, wp.update_at
            FROM work_plan_weekly wp
            JOIN division d ON d.division_id = wp.division_id
            JOIN team t ON t.team_id = wp.team_id
            LEFT JOIN employee le ON le.employee_id = t.leader_employee_id
            LEFT JOIN employee ce ON ce.employee_id = wp.created_by_id
            LEFT JOIN employee pe ON pe.employee_id = wp.approved_by_pm_id
            WHERE wp.weekly_plan_id = CAST(:plan AS uuid) AND wp.delete_at IS NULL
            """,
            {"plan": str(weekly_plan_id)},
        )
        if not wp:
            return None

        # Ambil daftar hari
        daily_rows = await self.fetchall(
            """
            SELECT wpd.daily_plan_id, wpd.weekly_plan_id, wpd.work_date,
                   wpd.site_name, wpd.site_lat, wpd.site_lng,
                   wpd.attendance_radius_m, wpd.clock_in_time, wpd.clock_out_time,
                   wpd.status, wpd.create_at, wpd.update_at
            FROM work_plan_daily wpd
            WHERE wpd.weekly_plan_id = CAST(:plan AS uuid) AND wpd.delete_at IS NULL
            ORDER BY wpd.work_date ASC
            """,
            {"plan": str(weekly_plan_id)},
        )

        # Ambil seluruh item tugas
        item_rows = await self.fetchall(
            """
            SELECT wpi.item_id, wpi.daily_plan_id, wpi.weekly_plan_id,
                   wpi.work_type_id, wt.name AS work_type_name,
                   wpi.title, wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                   wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                   wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                   wpi.allocated_to_weekly_id, wpi.delay_reason,
                   wpi.completion_id, wc.client_name, wc.project_title, wc.order_number,
                   wpi.start_time, wpi.end_time, wpi.location_name,
                   wpi.site_lat, wpi.site_lng, wpi.assigned_employee_ids,
                   wpi.create_at, wpi.update_at
            FROM work_plan_item wpi
            JOIN work_type wt ON wt.work_type_id = wpi.work_type_id
            LEFT JOIN work_completion wc ON wc.completion_id = wpi.completion_id
            WHERE wpi.weekly_plan_id = CAST(:plan AS uuid) AND wpi.delete_at IS NULL
            ORDER BY wpi.daily_plan_id, wpi.start_time ASC NULLS LAST, wpi.create_at ASC
            """,
            {"plan": str(weekly_plan_id)},
        )

        items_by_day: dict[UUID, list[PlanItemOut]] = {}
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
                    weekly_plan_id=it.weekly_plan_id,
                    work_type_id=it.work_type_id,
                    work_type_name=it.work_type_name,
                    title=it.title,
                    target_qty=it.target_qty,
                    completed_qty=it.completed_qty,
                    progress_percent=it.progress_percent,
                    status=it.status,
                    rollover_approval_status=it.rollover_approval_status,
                    approved_by_pm_id=it.approved_by_pm_id,
                    origin_item_id=it.origin_item_id,
                    shifted_to_daily_id=it.shifted_to_daily_id,
                    allocated_to_weekly_id=it.allocated_to_weekly_id,
                    delay_reason=it.delay_reason,
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

        days_out = [
            DailyPlanOut(
                daily_plan_id=d.daily_plan_id,
                weekly_plan_id=d.weekly_plan_id,
                work_date=d.work_date,
                site_name=d.site_name,
                site_lat=d.site_lat,
                site_lng=d.site_lng,
                attendance_radius_m=d.attendance_radius_m,
                clock_in_time=d.clock_in_time,
                clock_out_time=d.clock_out_time,
                status=d.status,
                is_holiday=(d.status == "HOLIDAY"),
                items=items_by_day.get(d.daily_plan_id, []),
                create_at=d.create_at,
                update_at=d.update_at,
            )
            for d in daily_rows
        ]

        return WeeklyPlanDetailOut(
            weekly_plan_id=wp.weekly_plan_id,
            division_id=wp.division_id,
            division_name=wp.division_name,
            team_id=wp.team_id,
            team_name=wp.team_name,
            leader_name=wp.leader_name,
            leader_employee_id=wp.leader_employee_id,
            week_number=wp.week_number,
            year=wp.year,
            start_date=wp.start_date,
            end_date=wp.end_date,
            created_by_id=wp.created_by_id,
            created_by_name=wp.created_by_name,
            approved_by_pm_id=wp.approved_by_pm_id,
            approved_by_pm_name=wp.approved_by_pm_name,
            status=wp.status,
            days=days_out,
            create_at=wp.create_at,
            update_at=wp.update_at,
        )

    async def create_weekly_plan(
        self,
        creator_employee_id: UUID,
        payload: WeeklyPlanCreateIn,
    ) -> WeeklyPlanDetailOut:
        """Membuat rencana kerja mingguan baru beserta hari dan item tugas jika disertakan."""
        res = await self.fetchone(
            """
            INSERT INTO work_plan_weekly (
                division_id, team_id, week_number, year, start_date, end_date,
                created_by_id, approved_by_pm_id, status
            )
            VALUES (
                CAST(:div_id AS uuid),
                CAST(:team_id AS uuid),
                CAST(:week_num AS smallint),
                CAST(:year AS smallint),
                CAST(:start_date AS date),
                CAST(:end_date AS date),
                CAST(:creator_id AS uuid),
                COALESCE(
                    (SELECT pm_id FROM division WHERE division_id = CAST(:div_id AS uuid)),
                    CAST(:creator_id AS uuid)
                ),
                CAST(:status AS varchar)

            )
            RETURNING weekly_plan_id
            """,
            {
                "div_id": str(payload.division_id),
                "team_id": str(payload.team_id),
                "week_num": payload.week_number,
                "year": payload.year,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "creator_id": str(creator_employee_id),
                "status": payload.status,
            },
        )
        weekly_plan_id = res.weekly_plan_id

        # Simpan hari-hari jika disertakan dalam pembuatan awal
        for d in payload.days:
            day_res = await self.fetchone(
                """
                INSERT INTO work_plan_daily (
                    weekly_plan_id, work_date, site_name, site_lat, site_lng,
                    attendance_radius_m, clock_in_time, clock_out_time, status
                )
                VALUES (
                    CAST(:plan AS uuid),
                    CAST(:work_date AS date),
                    :site_name,
                    CAST(:site_lat AS numeric),
                    CAST(:site_lng AS numeric),
                    CAST(:radius AS integer),
                    CAST(:clock_in AS time),
                    CAST(:clock_out AS time),
                    CAST(:status AS varchar)
                )
                RETURNING daily_plan_id
                """,
                {
                    "plan": str(weekly_plan_id),
                    "work_date": d.work_date,
                    "site_name": d.site_name,
                    "site_lat": d.site_lat,
                    "site_lng": d.site_lng,
                    "radius": d.attendance_radius_m,
                    "clock_in": d.clock_in_time,
                    "clock_out": d.clock_out_time,
                    "status": "HOLIDAY" if d.is_holiday else d.status,
                },
            )
            daily_plan_id = day_res.daily_plan_id

            # Simpan slot tugas untuk hari ini
            for it in d.items:
                assigned_json = json.dumps([str(uid) for uid in it.assigned_employee_ids])
                await self.execute(
                    """
                    INSERT INTO work_plan_item (
                        daily_plan_id, weekly_plan_id, work_type_id, title,
                        target_qty, completed_qty, progress_percent, status,
                        rollover_approval_status, completion_id, start_time, end_time,
                        location_name, site_lat, site_lng, assigned_employee_ids
                    )
                    VALUES (
                        CAST(:day_id AS uuid),
                        CAST(:plan_id AS uuid),
                        CAST(:wt_id AS uuid),
                        :title,
                        CAST(:target_qty AS numeric),
                        CAST(:comp_qty AS numeric),
                        CAST(:prog AS numeric),
                        CAST(:status AS varchar),
                        'NONE',
                        CAST(:completion_id AS uuid),
                        CAST(:start_time AS time),
                        CAST(:end_time AS time),
                        :loc_name,
                        CAST(:site_lat AS numeric),
                        CAST(:site_lng AS numeric),
                        CAST(:assigned AS jsonb)
                    )
                    """,
                    {
                        "day_id": str(daily_plan_id),
                        "plan_id": str(weekly_plan_id),
                        "wt_id": str(it.work_type_id),
                        "title": it.title,
                        "target_qty": it.target_qty,
                        "comp_qty": it.completed_qty,
                        "prog": it.progress_percent,
                        "status": it.status,
                        "completion_id": str(it.completion_id) if it.completion_id else None,
                        "start_time": it.start_time,
                        "end_time": it.end_time,
                        "loc_name": it.location_name,
                        "site_lat": it.site_lat if it.site_lat is not None else d.site_lat,
                        "site_lng": it.site_lng if it.site_lng is not None else d.site_lng,
                        "assigned": assigned_json,
                    },
                )

        detail = await self.get_weekly_plan_detail(weekly_plan_id)
        assert detail is not None
        return detail

    async def update_weekly_plan(
        self,
        weekly_plan_id: UUID,
        payload: WeeklyPlanUpdateIn,
    ) -> WeeklyPlanDetailOut | None:
        """Memperbarui rencana kerja mingguan."""
        await self.execute(
            """
            UPDATE work_plan_weekly
            SET division_id = COALESCE(CAST(:div_id AS uuid), division_id),
                team_id = COALESCE(CAST(:team_id AS uuid), team_id),
                week_number = COALESCE(CAST(:week_num AS smallint), week_number),
                year = COALESCE(CAST(:year AS smallint), year),
                start_date = COALESCE(CAST(:start_date AS date), start_date),
                end_date = COALESCE(CAST(:end_date AS date), end_date),
                status = COALESCE(CAST(:status AS varchar), status),
                update_at = now()
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND delete_at IS NULL
            """,
            {
                "plan": str(weekly_plan_id),
                "div_id": str(payload.division_id) if payload.division_id else None,
                "team_id": str(payload.team_id) if payload.team_id else None,
                "week_num": payload.week_number,
                "year": payload.year,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "status": payload.status,
            },
        )
        return await self.get_weekly_plan_detail(weekly_plan_id)

    async def delete_weekly_plan(self, weekly_plan_id: UUID) -> bool:
        """Soft-delete rencana kerja mingguan beserta seluruh hari dan item terkait."""
        # 1. Soft-delete items
        await self.execute(
            """
            UPDATE work_plan_item
            SET delete_at = now()
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND delete_at IS NULL
            """,
            {"plan": str(weekly_plan_id)},
        )
        # 2. Soft-delete daily plans
        await self.execute(
            """
            UPDATE work_plan_daily
            SET delete_at = now()
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND delete_at IS NULL
            """,
            {"plan": str(weekly_plan_id)},
        )
        # 3. Soft-delete weekly plan
        res = await self.execute(
            """
            UPDATE work_plan_weekly
            SET delete_at = now()
            WHERE weekly_plan_id = CAST(:plan AS uuid) AND delete_at IS NULL
            """,
            {"plan": str(weekly_plan_id)},
        )
        return bool(res.rowcount > 0)

    # ── DAILY PLAN CRUD ───────────────────────────────────────────

    async def get_daily_plan(self, daily_plan_id: UUID) -> DailyPlanOut | None:
        """Mengambil satu hari kerja beserta slot tugasnya."""
        d = await self.fetchone(
            """
            SELECT daily_plan_id, weekly_plan_id, work_date, site_name,
                   site_lat, site_lng, attendance_radius_m, clock_in_time,
                   clock_out_time, status, create_at, update_at
            FROM work_plan_daily
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {"day": str(daily_plan_id)},
        )
        if not d:
            return None

        # Ambil items untuk hari ini
        item_rows = await self.fetchall(
            """
            SELECT wpi.item_id, wpi.daily_plan_id, wpi.weekly_plan_id,
                   wpi.work_type_id, wt.name AS work_type_name,
                   wpi.title, wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                   wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                   wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                   wpi.allocated_to_weekly_id, wpi.delay_reason,
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
                    weekly_plan_id=it.weekly_plan_id,
                    work_type_id=it.work_type_id,
                    work_type_name=it.work_type_name,
                    title=it.title,
                    target_qty=it.target_qty,
                    completed_qty=it.completed_qty,
                    progress_percent=it.progress_percent,
                    status=it.status,
                    rollover_approval_status=it.rollover_approval_status,
                    approved_by_pm_id=it.approved_by_pm_id,
                    origin_item_id=it.origin_item_id,
                    shifted_to_daily_id=it.shifted_to_daily_id,
                    allocated_to_weekly_id=it.allocated_to_weekly_id,
                    delay_reason=it.delay_reason,
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
            weekly_plan_id=d.weekly_plan_id,
            work_date=d.work_date,
            site_name=d.site_name,
            site_lat=d.site_lat,
            site_lng=d.site_lng,
            attendance_radius_m=d.attendance_radius_m,
            clock_in_time=d.clock_in_time,
            clock_out_time=d.clock_out_time,
            status=d.status,
            is_holiday=(d.status == "HOLIDAY"),
            items=items_out,
            create_at=d.create_at,
            update_at=d.update_at,
        )

    async def create_daily_plan(self, payload: DailyPlanCreateIn) -> DailyPlanOut:
        """Membuat hari kerja baru."""
        res = await self.fetchone(
            """
            INSERT INTO work_plan_daily (
                weekly_plan_id, work_date, site_name, site_lat, site_lng,
                attendance_radius_m, clock_in_time, clock_out_time, status
            )
            VALUES (
                CAST(:plan AS uuid),
                CAST(:work_date AS date),
                :site_name,
                CAST(:site_lat AS numeric),
                CAST(:site_lng AS numeric),
                CAST(:radius AS integer),
                CAST(:clock_in AS time),
                CAST(:clock_out AS time),
                CAST(:status AS varchar)
            )
            RETURNING daily_plan_id
            """,
            {
                "plan": str(payload.weekly_plan_id),
                "work_date": payload.work_date,
                "site_name": payload.site_name,
                "site_lat": payload.site_lat,
                "site_lng": payload.site_lng,
                "radius": payload.attendance_radius_m,
                "clock_in": payload.clock_in_time,
                "clock_out": payload.clock_out_time,
                "status": "HOLIDAY" if payload.is_holiday else payload.status,
            },
        )
        daily_plan_id = res.daily_plan_id
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
            SET work_date = COALESCE(CAST(:work_date AS date), work_date),
                site_name = COALESCE(:site_name, site_name),
                site_lat = COALESCE(CAST(:site_lat AS numeric), site_lat),
                site_lng = COALESCE(CAST(:site_lng AS numeric), site_lng),
                attendance_radius_m = COALESCE(CAST(:radius AS integer), attendance_radius_m),
                clock_in_time = COALESCE(CAST(:clock_in AS time), clock_in_time),
                clock_out_time = COALESCE(CAST(:clock_out AS time), clock_out_time),
                status = COALESCE(CAST(:status AS varchar), status),
                update_at = now()
            WHERE daily_plan_id = CAST(:day AS uuid) AND delete_at IS NULL
            """,
            {
                "day": str(daily_plan_id),
                "work_date": payload.work_date,
                "site_name": payload.site_name,
                "site_lat": payload.site_lat,
                "site_lng": payload.site_lng,
                "radius": payload.attendance_radius_m,
                "clock_in": payload.clock_in_time,
                "clock_out": payload.clock_out_time,
                "status": "HOLIDAY" if payload.is_holiday else payload.status,
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
            SELECT wpi.item_id, wpi.daily_plan_id, wpi.weekly_plan_id,
                   wpi.work_type_id, wt.name AS work_type_name,
                   wpi.title, wpi.target_qty, wpi.completed_qty, wpi.progress_percent,
                   wpi.status, wpi.rollover_approval_status::text AS rollover_approval_status,
                   wpi.approved_by_pm_id, wpi.origin_item_id, wpi.shifted_to_daily_id,
                   wpi.allocated_to_weekly_id, wpi.delay_reason,
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
            weekly_plan_id=it.weekly_plan_id,
            work_type_id=it.work_type_id,
            work_type_name=it.work_type_name,
            title=it.title,
            target_qty=it.target_qty,
            completed_qty=it.completed_qty,
            progress_percent=it.progress_percent,
            status=it.status,
            rollover_approval_status=it.rollover_approval_status,
            approved_by_pm_id=it.approved_by_pm_id,
            origin_item_id=it.origin_item_id,
            shifted_to_daily_id=it.shifted_to_daily_id,
            allocated_to_weekly_id=it.allocated_to_weekly_id,
            delay_reason=it.delay_reason,
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
        # Jika weekly_plan_id belum ada, ambil dari daily_plan
        assigned_json = json.dumps([str(uid) for uid in payload.assigned_employee_ids])

        res = await self.fetchone(
            """
            INSERT INTO work_plan_item (
                daily_plan_id,
                weekly_plan_id,
                work_type_id,
                title,
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
                assigned_employee_ids
            )
            VALUES (
                CAST(:day_id AS uuid),
                COALESCE(
                    CAST(:plan_id AS uuid),
                    (SELECT weekly_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:day_id AS uuid))
                ),
                CAST(:wt_id AS uuid),
                :title,
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
                CAST(:assigned AS jsonb)
            )
            RETURNING item_id
            """,
            {
                "day_id": str(payload.daily_plan_id),
                "plan_id": str(payload.weekly_plan_id) if payload.weekly_plan_id else None,
                "wt_id": str(payload.work_type_id),
                "title": payload.title,
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

        await self.execute(
            """
            UPDATE work_plan_item
            SET title = COALESCE(:title, title),
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
                update_at = now()
            WHERE item_id = CAST(:item AS uuid) AND delete_at IS NULL
            """,
            {
                "item": str(item_id),
                "title": payload.title,
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

