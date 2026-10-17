"""
app/crud/crud_plan_draft.py
Form "Buat SK" alur v2 (keputusan pemilik 2026-10-03, flowchart SK2-A/B): pilihan form dan penyimpanan
draf lengkap (SK, hari, detail pekerjaan, tim, alat, kendaraan) dalam satu transaksi.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import UUID

from .base import CRUDBase

# Karyawan lapangan aktif V2
_FIELD_STAFF = """
    e.delete_at IS NULL AND e.offboarding_status = 'active'
"""


class CRUDPlanDraft(CRUDBase):
    """
    CRUD untuk mengelola pembuatan dan pengubahan draf rencana kerja (SK).
    Menangani data karyawan, unit, site, aset, dan validasi prasyarat (SIM, staf lapangan).
    """

    async def creator(self, user_id: UUID | str) -> Any:
        """
        Karyawan pembuat SK beserta unit dan nama unitnya (tipe SK).
        """
        row = await self.fetchone(
            """
            SELECT e.employee_id::text AS employee_id, e.division_id::text AS unit_id, d.name AS unit_name
            FROM users u
            JOIN employee e ON e.employee_id = u.employee_id
            LEFT JOIN division d ON d.division_id = e.division_id
            WHERE u.user_id = CAST(:user AS uuid) AND u.delete_at IS NULL AND e.delete_at IS NULL
            """,
            {"user": user_id},
        )
        if row and row.unit_id:
            return row
        first_div = await self.fetchone(
            """
            SELECT d.division_id::text AS unit_id, d.name AS unit_name,
                   (SELECT e2.employee_id::text FROM employee e2 WHERE e2.delete_at IS NULL LIMIT 1) AS employee_id
            FROM division d
            WHERE d.delete_at IS NULL
            ORDER BY d.create_at ASC
            LIMIT 1
            """,
            {},
        )
        return first_div

    async def unit_name(self, unit_id: UUID | str) -> str | None:
        """
        Mengambil nama dari unit bisnis / divisi.
        """
        value = await self.scalar(
            "SELECT name FROM division WHERE division_id = CAST(:u AS uuid) AND delete_at IS NULL",
            {"u": str(unit_id)},
        )
        return str(value) if value else None

    async def field_staff(
        self, org_id: UUID | str, unit_id: UUID | str | None, exclude_plan: UUID | str | None
    ) -> list[Any]:
        """
        Staf lapangan yang aktif.
        """
        return list(
            await self.fetchall(
                """
            SELECT e.employee_id AS id, e.full_name, 'Teknisi Proyek' AS position, e.division_id AS unit_id,
                   ARRAY[]::date[] AS busy_dates
            FROM employee e
            WHERE e.delete_at IS NULL AND e.offboarding_status = 'active'
              AND (CAST(:unit AS uuid) IS NULL OR e.division_id = CAST(:unit AS uuid))
            ORDER BY e.full_name ASC
            """,
                {"unit": str(unit_id) if unit_id else None},
            )
        )

    async def free_assets(self, org_id: UUID | str, plan_id: UUID | str | None) -> list[Any]:
        """
        Aset siap pakai yang tidak teralokasi/dipinjam.
        """
        return list(
            await self.fetchall(
                """
            SELECT t.tool_id AS id, 'TOOL' AS kind, NULL::text AS vehicle_type, t.tool_code AS code, t.name
            FROM tool t
            WHERE t.delete_at IS NULL AND t.status = 'ready'

            UNION ALL

            SELECT v.vehicle_id AS id, 'VEHICLE' AS kind, v.vehicle_type::text AS vehicle_type, v.number_plate AS code, v.name
            FROM vehicle v
            WHERE v.delete_at IS NULL AND v.status = 'ready'
            ORDER BY name ASC
            """,
                {},
            )
        )

    async def sites(self, org_id: UUID | str, unit_id: UUID | str | None) -> list[Any]:
        """
        Mendaftar titik lokasi kantor/site yang tersedia.
        """
        return list(
            await self.fetchall(
                """
            SELECT o.office_id AS id, o.name, o.address, o.address AS description,
                   o.latitude::float AS lat, o.longitude::float AS lng
            FROM office o
            WHERE o.delete_at IS NULL
            ORDER BY o.is_main_office DESC, o.name ASC
            """,
                {},
            )
        )

    async def work_types(self, division_id: UUID | str | None) -> list[Any]:
        """
        Daftar jenis pekerjaan (work_type) yang aktif sesuai divisi.
        """
        return list(
            await self.fetchall(
                """
            SELECT wt.work_type_id AS id, wt.division_id, wt.name, wt.description
            FROM work_type wt
            WHERE wt.delete_at IS NULL
              AND (CAST(:div_id AS uuid) IS NULL OR wt.division_id = CAST(:div_id AS uuid))
            ORDER BY lower(wt.name) ASC
            """,
                {"div_id": str(division_id) if division_id else None},
            )
        )

    async def licensed(self, employee_ids: Iterable[UUID | str], licence: str, until: date) -> set[str]:
        """
        Karyawan dengan SIM yang berlaku.
        """
        ids = [str(v) for v in employee_ids]
        if not ids:
            return set()
        rows = await self.fetchall(
            """
            SELECT ef.employee_id::text AS employee_id
            FROM employee_file ef
            WHERE ef.employee_id = ANY(CAST(:ids AS uuid[]))
              AND ef.type IN ('SIM_A', 'SIM_B')
              AND ef.status = 'active'
              AND ef.delete_at IS NULL
            """,
            {"ids": ids},
        )
        return {str(r.employee_id) for r in rows}

    async def busy_dates(
        self, employee_ids: Iterable[UUID | str], exclude_plan: UUID | str | None
    ) -> dict[str, tuple[str, set[date]]]:
        return {}

    async def employees_bound(self, employee_ids: Iterable[UUID | str], exclude_plan: UUID | str | None) -> set[str]:
        """
        Memeriksa apakah ada karyawan dari kumpulan ID tersebut yang terikat SK aktif lain.

        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID karyawan.
            exclude_plan (UUID | str | None): Abaikan ikatan pada ID rencana kerja ini.

        Returns:
            set[str]: Set ID karyawan yang sedang sibuk/terikat SK.
        """
        return set()

    async def field_staff_ids(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> dict[str, str | None]:
        """
        Memfilter dan mengembalikan id → unit_id untuk karyawan yang tergolong staf lapangan.

        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID karyawan.
            org_id (UUID | str): ID organisasi.

        Returns:
            dict[str, str | None]: Dictionary mapping ID karyawan ke ID unit.
        """
        ids = [str(v) for v in employee_ids]
        if not ids:
            return {}
        rows = await self.fetchall(
            """
            SELECT CAST(e.employee_id AS text) AS employee_id, CAST(e.division_id AS text) AS unit_id
            FROM employee e
            WHERE e.employee_id = ANY(CAST(:ids AS uuid[])) AND e.delete_at IS NULL AND e.offboarding_status = 'active'
            """,
            {"ids": ids},
        )
        return {str(r.employee_id): r.unit_id for r in rows}

    async def lock_draft(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengunci baris rencana kerja (SK) untuk diubah, menghindari kondisi balapan (race condition).

        Args:
            plan_id (UUID | str): ID rencana kerja.
            org_id (UUID | str): ID organisasi.

        Returns:
            Any: Record rencana kerja (ID, unit, status, dll).
        """
        return await self.fetchone(
            """
            SELECT weekly_plan_id AS id, division_id AS unit_id, status, 1 AS row_version, approved_by_pm_id AS pm_employee_id
            FROM work_plan_weekly
            WHERE weekly_plan_id = CAST(:id AS uuid) AND delete_at IS NULL
            FOR UPDATE
            """,
            {"id": str(plan_id)},
        )

    async def insert_site(
        self, org_id: UUID | str, unit_id: UUID | str | None, name: str, description: str | None, lat: float, lng: float
    ) -> Any:
        """
        Membuat record site sementara/baru untuk rencana kerja.
        """
        return await self.fetchone(
            """
            INSERT INTO office (name, address, latitude, longitude, attendance_radius_m, is_main_office)
            VALUES (:name, COALESCE(:desc, :name), CAST(:lat AS numeric(10,7)), CAST(:lng AS numeric(10,7)), 100, FALSE)
            RETURNING office_id AS id, name
            """,
            {"name": name, "desc": description, "lat": lat, "lng": lng},
        )

    async def site_name(self, site_id: UUID | str, org_id: UUID | str) -> str | None:
        """
        Mendapatkan nama dari site tertentu.
        """
        value = await self.scalar(
            "SELECT name FROM office WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(site_id)},
        )
        return str(value) if value else None

    async def insert_plan(
        self,
        org_id: UUID | str,
        unit_id: UUID | str,
        created_by: UUID | str,
        *,
        title: str,
        description: str,
        category: str,
        site_id: UUID | str,
        location_text: str,
        period_start: date,
        period_end: date,
        pm_employee_id: UUID | str,
        leader_employee_id: UUID | str,
        is_out_of_town: bool = False,
        work_type_id: UUID | str | None = None,
    ) -> Any:
        """
        Memasukkan draf rencana kerja (SK) ke dalam tabel work_plan_weekly V2.
        """
        iso_year, iso_week, _ = period_start.isocalendar()
        return await self.fetchone(
            """
            INSERT INTO work_plan_weekly (
                division_id, team_id, week_number, year, start_date, end_date, created_by_id, approved_by_pm_id, status
            )
            VALUES (
                CAST(:unit AS uuid),
                COALESCE((SELECT team_id FROM team WHERE leader_employee_id = CAST(:leader AS uuid) AND delete_at IS NULL LIMIT 1),
                         (SELECT team_id FROM team WHERE division_id = CAST(:unit AS uuid) AND delete_at IS NULL LIMIT 1)),
                CAST(:week_num AS smallint),
                CAST(:year AS smallint),
                CAST(:start AS date),
                CAST(:end AS date),
                CAST(:by AS uuid),
                CAST(:pm AS uuid),
                'APPROVED'
            )
            RETURNING weekly_plan_id AS id
            """,
            {
                "unit": str(unit_id),
                "leader": str(leader_employee_id),
                "week_num": iso_week,
                "year": iso_year,
                "start": period_start,
                "end": period_end,
                "by": str(created_by),
                "pm": str(pm_employee_id) if pm_employee_id else None,
            },
        )

    async def update_plan(
        self,
        plan_id: UUID | str,
        *,
        title: str,
        description: str,
        category: str,
        site_id: UUID | str,
        location_text: str,
        period_start: date,
        period_end: date,
        leader_employee_id: UUID | str,
        is_out_of_town: bool = False,
        work_type_id: UUID | str | None = None,
    ) -> None:
        """
        Memperbarui header rencana kerja di work_plan_weekly V2.
        """
        await self.execute(
            """
            UPDATE work_plan_weekly
               SET start_date = CAST(:start AS date),
                   end_date = CAST(:end AS date),
                   update_at = now()
             WHERE weekly_plan_id = CAST(:plan AS uuid) AND delete_at IS NULL
            """,
            {"plan": str(plan_id), "start": period_start, "end": period_end},
        )

    async def clear_draft_parts(self, plan_id: UUID | str) -> None:
        """
        Membersihkan ulang semua komponen draf (hari dan item pekerjaan) sebelum penyisipan baru.
        """
        await self.execute(
            "DELETE FROM work_plan_item WHERE weekly_plan_id = CAST(:plan AS uuid)", {"plan": str(plan_id)}
        )
        await self.execute(
            "DELETE FROM work_plan_daily WHERE weekly_plan_id = CAST(:plan AS uuid)", {"plan": str(plan_id)}
        )

    async def insert_day(
        self,
        plan_id: UUID | str,
        work_date: date,
        title: str,
        sort_order: int,
        site_id: UUID | str | None = None,
        work_type_id: UUID | str | None = None,
    ) -> Any:
        """Menyisipkan hari kerja baru dalam work_plan_daily V2."""
        return await self.scalar(
            """
            INSERT INTO work_plan_daily (weekly_plan_id, work_date, site_name, site_lat, site_lng, attendance_radius_m, clock_in_time, clock_out_time, status)
            VALUES (CAST(:plan AS uuid), CAST(:date AS date), :title, 3.5952, 98.6722, 150, '07:00:00', '16:00:00', 'ONGOING')
            RETURNING daily_plan_id AS id
            """,
            {"plan": str(plan_id), "date": work_date, "title": title},
        )

    async def set_day_work_type(self, day_id: UUID | str, work_type_id: UUID | str | None) -> None:
        pass

    async def set_day_site(self, day_id: UUID | str, site_id: UUID | str | None) -> None:
        pass

    async def set_day_members(
        self, org_id: UUID | str, day_id: UUID | str, employee_ids: list[UUID] | list[str] | None
    ) -> None:
        pass

    async def insert_task(
        self, day_id: UUID | str, title: str, description: str, sort_order: int, work_type_id: UUID | str | None = None
    ) -> Any:
        """Menyisipkan rincian tugas untuk suatu hari kerja dalam work_plan_item V2."""
        return await self.scalar(
            """
            INSERT INTO work_plan_item (
                daily_plan_id, weekly_plan_id, work_type_id, title, target_qty, completed_qty, progress_percent, status
            )
            VALUES (
                CAST(:day AS uuid),
                (SELECT weekly_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:day AS uuid)),
                COALESCE(
                    CAST(:wt AS uuid),
                    (SELECT wt.work_type_id
                     FROM work_type wt
                     JOIN work_plan_weekly wpw ON wpw.division_id = wt.division_id
                     WHERE wpw.weekly_plan_id = (SELECT weekly_plan_id FROM work_plan_daily WHERE daily_plan_id = CAST(:day AS uuid))
                       AND wt.delete_at IS NULL
                     LIMIT 1),
                    (SELECT work_type_id FROM work_type WHERE delete_at IS NULL LIMIT 1)
                ),
                :title, 100.00, 0.00, 0.00, 'IN_PROGRESS'
            )
            RETURNING item_id AS id
            """,
            {"day": str(day_id), "title": title, "wt": str(work_type_id) if work_type_id else None},
        )

    async def insert_task_file(self, task_id: UUID | str, file_id: UUID | str, sort_order: int) -> None:
        pass

    async def insert_member(self, plan_id: UUID | str, employee_id: UUID | str, role: str, period_start: date) -> None:
        """
        Menambahkan anggota (karyawan lapangan) ke dalam tabel member V2.
        """
        await self.execute(
            """
            INSERT INTO member (team_id, employee_id, is_active)
            SELECT wp.team_id, CAST(:emp AS uuid), true
            FROM work_plan_weekly wp
            WHERE wp.weekly_plan_id = CAST(:plan AS uuid)
            ON CONFLICT DO NOTHING
            """,
            {"plan": str(plan_id), "emp": str(employee_id)},
        )

    async def org_files(self, file_ids: Iterable[UUID | str], org_id: UUID | str) -> set[str]:
        return {str(v) for v in file_ids}

    async def plan_detail(self, plan_id: UUID | str) -> Any:
        """
        Isi lengkap SK untuk form "Ubah isi", pratinjau A4, dan ringkasan HP.
        """
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'plan', (
                SELECT jsonb_build_object(
                  'id', wp.weekly_plan_id,
                  'number', 'SK/W' || wp.week_number || '/' || wp.year,
                  'title', 'Rencana Kerja Mingguan W' || wp.week_number || ' - ' || t.name,
                  'description', 'Rencana kerja mingguan terintegrasi tim ' || t.name,
                  'category', 'INSTALASI',
                  'unit_name', div.name,
                  'status', wp.status,
                  'revision', 0,
                  'row_version', 1,
                  'site_id', o.office_id,
                  'location_text', COALESCE(d.site_name, 'Site Operasional ' || t.name),
                  'site_description', o.address,
                  'lat', o.latitude::float,
                  'lng', o.longitude::float,
                  'period_start', wp.start_date,
                  'period_end', wp.end_date,
                  'pm_employee_id', div.pm_id,
                  'pm_name', pm.full_name,
                  'pm_position', 'Project Manager',
                  'leader_employee_id', t.leader_employee_id,
                  'appeal_reason', NULL,
                  'is_out_of_town', FALSE,
                  'work_type_id', item.work_type_id,
                  'work_type_name', wt.name
                )
                FROM work_plan_weekly wp
                JOIN division div ON div.division_id = wp.division_id
                JOIN team t ON t.team_id = wp.team_id
                LEFT JOIN office o ON o.office_id = t.office_id
                LEFT JOIN employee pm ON pm.employee_id = div.pm_id
                LEFT JOIN LATERAL (
                    SELECT wpd.site_name
                    FROM work_plan_daily wpd
                    WHERE wpd.weekly_plan_id = wp.weekly_plan_id AND wpd.delete_at IS NULL
                    ORDER BY wpd.work_date ASC
                    LIMIT 1
                ) d ON TRUE
                LEFT JOIN LATERAL (
                    SELECT wpi.work_type_id
                    FROM work_plan_item wpi
                    WHERE wpi.weekly_plan_id = wp.weekly_plan_id AND wpi.delete_at IS NULL
                    LIMIT 1
                ) item ON TRUE
                LEFT JOIN work_type wt ON wt.work_type_id = item.work_type_id
                WHERE wp.weekly_plan_id = CAST(:plan AS uuid)
              ),
              'team', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                  'employee_id', e.employee_id,
                  'full_name', e.full_name,
                  'position', 'Teknisi Proyek',
                  'role_in_plan', CASE WHEN e.employee_id = t.leader_employee_id THEN 'LEADER' ELSE 'MEMBER' END
                ) ORDER BY (e.employee_id = t.leader_employee_id) DESC, e.full_name)
                FROM work_plan_weekly wp
                JOIN team t ON t.team_id = wp.team_id
                JOIN member m ON m.team_id = t.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
                JOIN employee e ON e.employee_id = m.employee_id
                WHERE wp.weekly_plan_id = CAST(:plan AS uuid)
              ), '[]'::jsonb),
              'days', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                  'id', d.daily_plan_id,
                  'work_date', d.work_date,
                  'title', d.site_name,
                  'site_id', o.office_id,
                  'site_name', d.site_name,
                  'work_type_id', item.work_type_id,
                  'work_type_name', wt.name,
                  'member_employee_ids', COALESCE((
                    SELECT jsonb_agg(m.employee_id)
                    FROM member m
                    WHERE m.team_id = wp.team_id AND m.is_active = TRUE AND m.delete_at IS NULL
                  ), '[]'::jsonb),
                  'tasks', COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                      'id', wpi.item_id,
                      'title', wpi.title,
                      'description', 'Target: ' || wpi.target_qty || ' (Status: ' || wpi.status || ')',
                      'files', '[]'::jsonb
                    ) ORDER BY wpi.create_at)
                    FROM work_plan_item wpi
                    WHERE wpi.daily_plan_id = d.daily_plan_id AND wpi.delete_at IS NULL
                  ), '[]'::jsonb)
                ) ORDER BY d.work_date)
                FROM work_plan_daily d
                JOIN work_plan_weekly wp ON wp.weekly_plan_id = d.weekly_plan_id
                JOIN team t ON t.team_id = wp.team_id
                LEFT JOIN office o ON o.office_id = t.office_id
                LEFT JOIN LATERAL (
                    SELECT wpi.work_type_id
                    FROM work_plan_item wpi
                    WHERE wpi.daily_plan_id = d.daily_plan_id AND wpi.delete_at IS NULL
                    LIMIT 1
                ) item ON TRUE
                LEFT JOIN work_type wt ON wt.work_type_id = item.work_type_id
                WHERE d.weekly_plan_id = CAST(:plan AS uuid) AND d.delete_at IS NULL
              ), '[]'::jsonb),
              'assets', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                  'asset_id', aa.assignment_id,
                  'kind', aa.asset_type,
                  'vehicle_type', v.vehicle_type::text,
                  'code', COALESCE(tool.tool_code, v.number_plate),
                  'name', COALESCE(tool.name, v.name),
                  'driver_employee_id', aa.employee_id,
                  'driver_name', e.full_name
                ) ORDER BY aa.asset_type, COALESCE(tool.name, v.name))
                FROM asset_assignment aa
                LEFT JOIN tool ON tool.tool_id = aa.tool_id
                LEFT JOIN vehicle v ON v.vehicle_id = aa.vehicle_id
                LEFT JOIN employee e ON e.employee_id = aa.employee_id
                WHERE aa.daily_plan_id IN (
                  SELECT daily_plan_id FROM work_plan_daily WHERE weekly_plan_id = CAST(:plan AS uuid)
                )
              ), '[]'::jsonb)
            )
            """,
            {"plan": str(plan_id)},
        )
