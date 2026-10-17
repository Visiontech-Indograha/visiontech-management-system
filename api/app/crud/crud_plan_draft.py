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

# Karyawan lapangan atau PM = akun aktif (bukan peran kantor lain seperti OPS, ADMIN, HR, FINANCE, ASSET).
_FIELD_STAFF = """
    e.is_active AND e.deleted_at IS NULL
    AND (e.attendance_mode = 'FIELD' OR EXISTS (
        SELECT 1 FROM vms.app_user pu JOIN vms.user_role prl ON prl.user_id = pu.id
        WHERE pu.employee_id = e.id AND pu.is_active AND prl.role = 'PM'
    ))
    AND EXISTS (SELECT 1 FROM vms.app_user fu WHERE fu.employee_id = e.id AND fu.is_active)
    AND NOT EXISTS (
        SELECT 1 FROM vms.app_user ou JOIN vms.user_role orl ON orl.user_id = ou.id
        WHERE ou.employee_id = e.id AND ou.is_active
          AND orl.role IN ('OPS', 'ADMIN', 'HR', 'FINANCE', 'ASSET'))
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

    async def field_staff(self, org_id: UUID | str, unit_id: UUID | str | None,
                          exclude_plan: UUID | str | None) -> list[Any]:
        """
        Staf lapangan yang aktif.
        """
        return list(await self.fetchall(
            """
            SELECT e.employee_id AS id, e.full_name, 'Teknisi Proyek' AS position, e.division_id AS unit_id,
                   ARRAY[]::date[] AS busy_dates
            FROM employee e
            WHERE e.delete_at IS NULL AND e.offboarding_status = 'active'
              AND (CAST(:unit AS uuid) IS NULL OR e.division_id = CAST(:unit AS uuid))
            ORDER BY e.full_name ASC
            """,
            {"unit": str(unit_id) if unit_id else None},
        ))

    async def free_assets(self, org_id: UUID | str, plan_id: UUID | str | None) -> list[Any]:
        """
        Aset siap pakai yang tidak teralokasi/dipinjam.
        """
        return list(await self.fetchall(
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
        ))

    async def sites(self, org_id: UUID | str, unit_id: UUID | str | None) -> list[Any]:
        """
        Mendaftar titik lokasi kantor/site yang tersedia.
        """
        return list(await self.fetchall(
            """
            SELECT o.office_id AS id, o.name, o.address, o.address AS description,
                   o.latitude::float AS lat, o.longitude::float AS lng
            FROM office o
            WHERE o.delete_at IS NULL
            ORDER BY o.is_main_office DESC, o.name ASC
            """,
            {},
        ))

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

    async def busy_dates(self, employee_ids: Iterable[UUID | str],
                         exclude_plan: UUID | str | None) -> dict[str, tuple[str, set[date]]]:
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
        ids = [str(v) for v in employee_ids]
        if not ids:
            return set()
        # Melakukan unnest array UUID lalu menggunakan fungsi bantu vms.employee_is_bound().
        rows = await self.fetchall(
            """
            SELECT CAST(x AS text) AS employee_id FROM unnest(CAST(:ids AS uuid[])) AS x
            WHERE vms.employee_is_bound(x, CAST(:plan AS uuid))
            """,
            {"ids": ids, "plan": str(exclude_plan) if exclude_plan else None},
        )
        return {str(r.employee_id) for r in rows}

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
        # Memastikan hanya karyawan yang sesuai dengan definisi _FIELD_STAFF yang masuk
        rows = await self.fetchall(
            f"""
            SELECT CAST(e.id AS text) AS employee_id, CAST(e.unit_id AS text) AS unit_id
            FROM vms.employee e
            WHERE e.id = ANY(CAST(:ids AS uuid[])) AND e.organization_id = CAST(:org AS uuid) AND {_FIELD_STAFF}
            """,
            {"ids": ids, "org": str(org_id)},
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
        # FOR UPDATE akan memblokir transaksi lain yang mencoba membaca atau mengubah
        # rencana kerja ini sampai transaksi saat ini selesai.
        return await self.fetchone(
            """
            SELECT id, unit_id, status, row_version, pm_employee_id
            FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": plan_id, "org": org_id},
        )

    async def insert_site(self, org_id: UUID | str, unit_id: UUID | str | None, name: str,
                          description: str | None, lat: float, lng: float) -> Any:
        """
        Membuat record site sementara/baru untuk rencana kerja.

        Args:
            org_id (UUID | str): ID organisasi.
            unit_id (UUID | str | None): ID unit yang memilikinya.
            name (str): Nama site.
            description (str | None): Penjelasan site.
            lat (float): Garis lintang (latitude).
            lng (float): Garis bujur (longitude).

        Returns:
            Any: Record site baru yang terbuat.
        """
        # Site dibuat dengan fungsi koordinat PostGIS ST_MakePoint.
        return await self.fetchone(
            """
            INSERT INTO vms.site (organization_id, name, address, description, location, radius_m, unit_id)
            VALUES (CAST(:org AS uuid), :name, :desc, :desc, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 100,
                    CAST(:unit AS uuid))
            RETURNING id, name
            """,
            {"org": str(org_id), "name": name, "desc": description, "lat": lat, "lng": lng,
             "unit": str(unit_id) if unit_id else None},
        )

    async def site_name(self, site_id: UUID | str, org_id: UUID | str) -> str | None:
        """
        Mendapatkan nama dari site tertentu.

        Args:
            site_id (UUID | str): ID site.
            org_id (UUID | str): ID organisasi.

        Returns:
            str | None: Nama site, atau None.
        """
        # Pengecekan site name dari vms.site dan memastikan tidak dalam keadaan dihapus.
        value = await self.scalar(
            "SELECT name FROM vms.site WHERE id = CAST(:id AS uuid) AND organization_id = CAST(:org AS uuid) "
            "AND deleted_at IS NULL",
            {"id": str(site_id), "org": str(org_id)})
        return str(value) if value else None

    async def insert_plan(self, org_id: UUID | str, unit_id: UUID | str, created_by: UUID | str, *,
                          title: str, description: str, category: str, site_id: UUID | str,
                          location_text: str, period_start: date, period_end: date,
                          pm_employee_id: UUID | str, leader_employee_id: UUID | str,
                          is_out_of_town: bool = False, work_type_id: UUID | str | None = None) -> Any:
        """
        Memasukkan draf rencana kerja (SK) ke dalam database untuk pertama kali.

        Args:
            (Beragam Parameter detail SK)

        Returns:
            Any: Menyertakan ID yang dihasilkan.
        """
        # Periode menggunakan daterange PostgreSQL, inklusif (tanda kurung '[]') dari awal hingga akhir.
        return await self.fetchone(
            """
            INSERT INTO vms.work_plan (organization_id, unit_id, site_id, title, location_text, description,
                                       category, period, pm_employee_id, leader_employee_id, status, created_by,
                                       is_out_of_town, work_type_id)
            VALUES (CAST(:org AS uuid), CAST(:unit AS uuid), CAST(:site AS uuid), :title, :loc, :desc,
                    :category, daterange(:start, :end, '[]'), CAST(:pm AS uuid), CAST(:leader AS uuid),
                    'DRAFT', CAST(:by AS uuid), :oot, CAST(:wt AS uuid))
            RETURNING id
            """,
            {"org": str(org_id), "unit": str(unit_id), "site": str(site_id), "title": title,
             "loc": location_text, "desc": description, "category": category, "start": period_start,
             "end": period_end, "pm": str(pm_employee_id), "leader": str(leader_employee_id),
             "by": str(created_by), "oot": is_out_of_town,
             "wt": str(work_type_id) if work_type_id else None},
        )

    async def update_plan(self, plan_id: UUID | str, *, title: str, description: str, category: str,
                          site_id: UUID | str, location_text: str, period_start: date, period_end: date,
                          leader_employee_id: UUID | str, is_out_of_town: bool = False,
                          work_type_id: UUID | str | None = None) -> None:
        """
        Memperbarui header/informasi umum rencana kerja (SK) saat pengeditan draf.

        Args:
            (Beragam parameter terkait)
        """
        # Menulis ulang properti draf SK dan menaikkan row_version sebagai antisipasi concurrency.
        await self.execute(
            """
            UPDATE vms.work_plan
               SET title = :title, description = :desc, category = :category, site_id = CAST(:site AS uuid),
                   location_text = :loc, period = daterange(:start, :end, '[]'),
                   leader_employee_id = CAST(:leader AS uuid), is_out_of_town = :oot,
                   work_type_id = CAST(:wt AS uuid), row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "title": title, "desc": description, "category": category, "site": str(site_id),
             "loc": location_text, "start": period_start, "end": period_end, "leader": str(leader_employee_id),
             "oot": is_out_of_town, "wt": str(work_type_id) if work_type_id else None},
        )

    async def clear_draft_parts(self, plan_id: UUID | str) -> None:
        """
        Membersihkan ulang semua komponen draf (hari, tugas, anggota, alokasi aset)
        sebelum menyisipkan data draf yang baru dari formulir klien.

        Args:
            plan_id (UUID | str): ID rencana kerja.
        """
        # Karena ini pembaruan utuh (replace-all) dari aplikasi web, hapus semua
        # record harian dan keanggotaan.
        await self.execute("DELETE FROM vms.work_plan_day WHERE work_plan_id = :plan", {"plan": plan_id})
        await self.execute("DELETE FROM vms.work_plan_member WHERE work_plan_id = :plan", {"plan": plan_id})
        # Aset dilepas dan statusnya dikembalikan ke 'AVAILABLE'.
        await self.execute(
            """
            WITH freed AS (
                UPDATE vms.asset_allocation SET released_at = now()
                 WHERE work_plan_id = :plan AND released_at IS NULL
                RETURNING asset_id
            )
            UPDATE vms.asset SET status = 'AVAILABLE', updated_at = now() WHERE id IN (SELECT asset_id FROM freed)
            """,
            {"plan": plan_id},
        )

    async def insert_day(self, plan_id: UUID | str, work_date: date, title: str, sort_order: int,
                         site_id: UUID | str | None = None, work_type_id: UUID | str | None = None) -> Any:
        """Menyisipkan hari kerja baru dalam draf (opsional dengan lokasi dan jenis pekerjaan khusus hari itu)."""
        # Menambah hari berdasarkan tanggal di work_date dan mereturn id hari.
        return await self.scalar(
            "INSERT INTO vms.work_plan_day (work_plan_id, work_date, title, sort_order, site_id, work_type_id) "
            "VALUES (:plan, :date, :title, :sort, CAST(:site AS uuid), CAST(:wt AS uuid)) RETURNING id",
            {"plan": plan_id, "date": work_date, "title": title, "sort": sort_order,
             "site": str(site_id) if site_id else None, "wt": str(work_type_id) if work_type_id else None},
        )

    async def set_day_work_type(self, day_id: UUID | str, work_type_id: UUID | str | None) -> None:
        """Jenis pekerjaan khusus satu hari (None = ikut jenis rencana)."""
        await self.execute(
            "UPDATE vms.work_plan_day SET work_type_id = CAST(:wt AS uuid) WHERE id = CAST(:day AS uuid)",
            {"day": str(day_id), "wt": str(work_type_id) if work_type_id else None})

    async def set_day_site(self, day_id: UUID | str, site_id: UUID | str | None) -> None:
        """Lokasi khusus satu hari (None = ikut lokasi rencana)."""
        await self.execute("UPDATE vms.work_plan_day SET site_id = CAST(:site AS uuid) WHERE id = CAST(:day AS uuid)",
                           {"day": str(day_id), "site": str(site_id) if site_id else None})

    async def set_day_members(self, org_id: UUID | str, day_id: UUID | str,
                              employee_ids: list[UUID] | list[str] | None) -> None:
        """Anggota yang bertugas pada satu hari. None/kosong = seluruh tim (tanpa baris)."""
        await self.execute("DELETE FROM vms.work_plan_day_member WHERE work_plan_day_id = CAST(:day AS uuid)",
                           {"day": str(day_id)})
        for employee_id in dict.fromkeys(str(e) for e in employee_ids or []):
            await self.execute(
                "INSERT INTO vms.work_plan_day_member (organization_id, work_plan_day_id, employee_id) "
                "VALUES (CAST(:org AS uuid), CAST(:day AS uuid), CAST(:emp AS uuid))",
                {"org": str(org_id), "day": str(day_id), "emp": employee_id})

    async def insert_task(self, day_id: UUID | str, title: str, description: str, sort_order: int) -> Any:
        """Menyisipkan rincian tugas untuk suatu hari kerja dalam draf."""
        # Menambahkan data task.
        return await self.scalar(
            "INSERT INTO vms.work_plan_task (work_plan_day_id, title, description, sort_order) "
            "VALUES (:day, :title, :desc, :sort) RETURNING id",
            {"day": day_id, "title": title, "desc": description, "sort": sort_order},
        )

    async def insert_task_file(self, task_id: UUID | str, file_id: UUID | str, sort_order: int) -> None:
        """Menyisipkan referensi dokumen (lampiran) ke sebuah tugas."""
        # Mereferensikan file dari file_object ke task ini.
        await self.execute(
            "INSERT INTO vms.work_plan_task_attachment (task_id, file_id, sort_order) VALUES (:task, :file, :sort)",
            {"task": task_id, "file": str(file_id), "sort": sort_order},
        )

    async def insert_member(self, plan_id: UUID | str, employee_id: UUID | str, role: str,
                            period_start: date) -> None:
        """
        Menambahkan anggota (karyawan lapangan) ke dalam tim SK.

        Args:
            plan_id (UUID | str): ID rencana kerja.
            employee_id (UUID | str): ID karyawan lapangan.
            role (str): Perannya dalam SK.
            period_start (date): Mulai aktif.
        """
        # Menyisipkan rentang waktu (valid_period) dengan daterange '[)'.
        await self.execute(
            """
            INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
            VALUES (:plan, CAST(:emp AS uuid), CAST(:role AS vms.role_code), daterange(CAST(:start AS date), NULL, '[)'))
            """,
            {"plan": plan_id, "emp": str(employee_id), "role": role, "start": period_start},
        )

    async def org_files(self, file_ids: Iterable[UUID | str], org_id: UUID | str) -> set[str]:
        """
        Memvalidasi kepemilikan file yang dilampirkan oleh suatu organisasi.

        Args:
            file_ids (Iterable[UUID | str]): ID daftar file yang dicek.
            org_id (UUID | str): ID organisasi terkait.

        Returns:
            set[str]: ID file yang ada dan valid milik organisasi tersebut.
        """
        ids = [str(v) for v in file_ids]
        if not ids:
            return set()
        # Query list pencarian file melalui relasi array ANY()
        rows = await self.fetchall(
            "SELECT CAST(id AS text) AS id FROM vms.file_object "
            "WHERE id = ANY(CAST(:ids AS uuid[])) AND organization_id = CAST(:org AS uuid)",
            {"ids": ids, "org": str(org_id)})
        return {str(r.id) for r in rows}

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
