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

# Karyawan lapangan = akun aktif tanpa peran kantor (R-26) dan absen lewat HP (R-33).
_FIELD_STAFF = """
    e.is_active AND e.deleted_at IS NULL AND e.attendance_mode = 'FIELD'
    AND EXISTS (SELECT 1 FROM vms.app_user fu WHERE fu.employee_id = e.id AND fu.is_active)
    AND NOT EXISTS (
        SELECT 1 FROM vms.app_user ou JOIN vms.user_role orl ON orl.user_id = ou.id
        WHERE ou.employee_id = e.id AND ou.is_active
          AND orl.role IN ('PM', 'OPS', 'ADMIN', 'HR', 'FINANCE', 'ASSET'))
"""


class CRUDPlanDraft(CRUDBase):

    async def creator(self, user_id: UUID | str) -> Any:
        """Karyawan pembuat SK beserta unit dan nama unitnya (tipe SK)."""
        return await self.fetchone(
            """
            SELECT e.id::text AS employee_id, e.unit_id::text AS unit_id, bu.name AS unit_name
            FROM vms.app_user u
            JOIN vms.employee e ON e.id = u.employee_id
            LEFT JOIN vms.business_unit bu ON bu.id = e.unit_id
            WHERE u.id = :user AND e.is_active AND e.deleted_at IS NULL
            """,
            {"user": user_id},
        )

    async def unit_name(self, unit_id: UUID | str) -> str | None:
        value = await self.scalar("SELECT name FROM vms.business_unit WHERE id = CAST(:u AS uuid)",
                                  {"u": str(unit_id)})
        return str(value) if value else None

    async def field_staff(self, org_id: UUID | str, unit_id: UUID | str | None,
                          exclude_plan: UUID | str | None) -> list[Any]:
        """Staf lapangan yang tidak terikat SK aktif mana pun. `unit_id` terisi = hanya bawahan unit itu."""
        return list(await self.fetchall(
            f"""
            SELECT e.id, e.full_name, e.position, e.unit_id
            FROM vms.employee e
            WHERE e.organization_id = CAST(:org AS uuid) AND {_FIELD_STAFF}
              AND (CAST(:unit AS uuid) IS NULL OR e.unit_id = CAST(:unit AS uuid))
              AND NOT vms.employee_is_bound(e.id, CAST(:plan AS uuid))
            ORDER BY e.full_name
            """,
            {"org": str(org_id), "unit": str(unit_id) if unit_id else None,
             "plan": str(exclude_plan) if exclude_plan else None},
        ))

    async def free_assets(self, org_id: UUID | str, plan_id: UUID | str | None) -> list[Any]:
        """Aset siap pakai yang tidak teralokasi/dipinjam — ditambah aset yang sudah dipesan draf ini."""
        return list(await self.fetchall(
            """
            SELECT a.id, CAST(a.kind AS text) AS kind, a.vehicle_type, a.code, a.name
            FROM vms.asset a
            WHERE a.organization_id = CAST(:org AS uuid) AND a.deleted_at IS NULL
              AND ((a.status = 'AVAILABLE'
                    AND NOT EXISTS (SELECT 1 FROM vms.asset_allocation al
                                     WHERE al.asset_id = a.id AND al.released_at IS NULL))
                   OR EXISTS (SELECT 1 FROM vms.asset_allocation al
                               WHERE al.asset_id = a.id AND al.released_at IS NULL
                                 AND al.work_plan_id = CAST(:plan AS uuid)))
            ORDER BY a.kind, a.name
            """,
            {"org": str(org_id), "plan": str(plan_id) if plan_id else None},
        ))

    async def sites(self, org_id: UUID | str, unit_id: UUID | str | None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT s.id, s.name, s.address, s.description,
                   ST_Y(s.location::geometry) AS lat, ST_X(s.location::geometry) AS lng
            FROM vms.site s
            WHERE s.organization_id = CAST(:org AS uuid) AND s.deleted_at IS NULL
              AND (CAST(:unit AS uuid) IS NULL OR s.unit_id IS NULL OR s.unit_id = CAST(:unit AS uuid))
            ORDER BY s.name
            """,
            {"org": str(org_id), "unit": str(unit_id) if unit_id else None},
        ))

    async def licensed(self, employee_ids: Iterable[UUID | str], licence: str, until: date) -> set[str]:
        """Karyawan dengan SIM `licence` yang berlaku sampai `until` (aturan trigger tg_vehicle_driver_licence)."""
        ids = [str(v) for v in employee_ids]
        if not ids:
            return set()
        rows = await self.fetchall(
            """
            SELECT CAST(employee_id AS text) AS employee_id FROM vms.employee_document
            WHERE employee_id = ANY(CAST(:ids AS uuid[])) AND doc_type = :licence AND lifecycle = 'CURRENT'
              AND (expiry_date IS NULL OR expiry_date >= :until)
            """,
            {"ids": ids, "licence": licence, "until": until},
        )
        return {str(r.employee_id) for r in rows}

    async def employees_bound(self, employee_ids: Iterable[UUID | str], exclude_plan: UUID | str | None) -> set[str]:
        ids = [str(v) for v in employee_ids]
        if not ids:
            return set()
        rows = await self.fetchall(
            """
            SELECT CAST(x AS text) AS employee_id FROM unnest(CAST(:ids AS uuid[])) AS x
            WHERE vms.employee_is_bound(x, CAST(:plan AS uuid))
            """,
            {"ids": ids, "plan": str(exclude_plan) if exclude_plan else None},
        )
        return {str(r.employee_id) for r in rows}

    async def field_staff_ids(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> dict[str, str | None]:
        """id → unit_id untuk karyawan yang memenuhi syarat staf lapangan."""
        ids = [str(v) for v in employee_ids]
        if not ids:
            return {}
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
        return await self.fetchone(
            """
            INSERT INTO vms.site (organization_id, name, address, description, location, unit_id)
            VALUES (CAST(:org AS uuid), :name, :desc, :desc, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
                    CAST(:unit AS uuid))
            RETURNING id, name
            """,
            {"org": str(org_id), "name": name, "desc": description, "lat": lat, "lng": lng,
             "unit": str(unit_id) if unit_id else None},
        )

    async def site_name(self, site_id: UUID | str, org_id: UUID | str) -> str | None:
        value = await self.scalar(
            "SELECT name FROM vms.site WHERE id = CAST(:id AS uuid) AND organization_id = CAST(:org AS uuid) "
            "AND deleted_at IS NULL",
            {"id": str(site_id), "org": str(org_id)})
        return str(value) if value else None

    async def insert_plan(self, org_id: UUID | str, unit_id: UUID | str, created_by: UUID | str, *,
                          title: str, description: str, category: str, site_id: UUID | str,
                          location_text: str, period_start: date, period_end: date,
                          pm_employee_id: UUID | str, leader_employee_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            INSERT INTO vms.work_plan (organization_id, unit_id, site_id, title, location_text, description,
                                       category, period, pm_employee_id, leader_employee_id, status, created_by)
            VALUES (CAST(:org AS uuid), CAST(:unit AS uuid), CAST(:site AS uuid), :title, :loc, :desc,
                    :category, daterange(:start, :end, '[]'), CAST(:pm AS uuid), CAST(:leader AS uuid),
                    'DRAFT', CAST(:by AS uuid))
            RETURNING id
            """,
            {"org": str(org_id), "unit": str(unit_id), "site": str(site_id), "title": title,
             "loc": location_text, "desc": description, "category": category, "start": period_start,
             "end": period_end, "pm": str(pm_employee_id), "leader": str(leader_employee_id),
             "by": str(created_by)},
        )

    async def update_plan(self, plan_id: UUID | str, *, title: str, description: str, category: str,
                          site_id: UUID | str, location_text: str, period_start: date, period_end: date,
                          leader_employee_id: UUID | str) -> None:
        await self.execute(
            """
            UPDATE vms.work_plan
               SET title = :title, description = :desc, category = :category, site_id = CAST(:site AS uuid),
                   location_text = :loc, period = daterange(:start, :end, '[]'),
                   leader_employee_id = CAST(:leader AS uuid), row_version = row_version + 1
             WHERE id = :plan
            """,
            {"plan": plan_id, "title": title, "desc": description, "category": category, "site": str(site_id),
             "loc": location_text, "start": period_start, "end": period_end, "leader": str(leader_employee_id)},
        )

    async def clear_draft_parts(self, plan_id: UUID | str) -> None:
        """Draf disusun ulang seluruhnya: hari (beserta tugas & lampirannya), tim, dan reservasi aset."""
        await self.execute("DELETE FROM vms.work_plan_day WHERE work_plan_id = :plan", {"plan": plan_id})
        await self.execute("DELETE FROM vms.work_plan_member WHERE work_plan_id = :plan", {"plan": plan_id})
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

    async def insert_day(self, plan_id: UUID | str, work_date: date, title: str, sort_order: int) -> Any:
        return await self.scalar(
            "INSERT INTO vms.work_plan_day (work_plan_id, work_date, title, sort_order) "
            "VALUES (:plan, :date, :title, :sort) RETURNING id",
            {"plan": plan_id, "date": work_date, "title": title, "sort": sort_order},
        )

    async def insert_task(self, day_id: UUID | str, title: str, description: str, sort_order: int) -> Any:
        return await self.scalar(
            "INSERT INTO vms.work_plan_task (work_plan_day_id, title, description, sort_order) "
            "VALUES (:day, :title, :desc, :sort) RETURNING id",
            {"day": day_id, "title": title, "desc": description, "sort": sort_order},
        )

    async def insert_task_file(self, task_id: UUID | str, file_id: UUID | str, sort_order: int) -> None:
        await self.execute(
            "INSERT INTO vms.work_plan_task_attachment (task_id, file_id, sort_order) VALUES (:task, :file, :sort)",
            {"task": task_id, "file": str(file_id), "sort": sort_order},
        )

    async def insert_member(self, plan_id: UUID | str, employee_id: UUID | str, role: str,
                            period_start: date) -> None:
        await self.execute(
            """
            INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
            VALUES (:plan, CAST(:emp AS uuid), CAST(:role AS vms.role_code), daterange(CAST(:start AS date), NULL, '[)'))
            """,
            {"plan": plan_id, "emp": str(employee_id), "role": role, "start": period_start},
        )

    async def org_files(self, file_ids: Iterable[UUID | str], org_id: UUID | str) -> set[str]:
        ids = [str(v) for v in file_ids]
        if not ids:
            return set()
        rows = await self.fetchall(
            "SELECT CAST(id AS text) AS id FROM vms.file_object "
            "WHERE id = ANY(CAST(:ids AS uuid[])) AND organization_id = CAST(:org AS uuid)",
            {"ids": ids, "org": str(org_id)})
        return {str(r.id) for r in rows}

    async def plan_detail(self, plan_id: UUID | str) -> Any:
        """Isi lengkap SK untuk form "Ubah isi", pratinjau A4, dan ringkasan HP."""
        return await self.scalar(
            """
            SELECT jsonb_build_object(
              'plan', (SELECT jsonb_build_object(
                    'id', wp.id, 'number', wp.number, 'title', wp.title, 'description', wp.description,
                    'category', wp.category, 'unit_name', bu.name, 'status', wp.status, 'revision', wp.revision,
                    'row_version', wp.row_version, 'site_id', wp.site_id, 'location_text', wp.location_text,
                    'site_description', s.description,
                    'lat', ST_Y(s.location::geometry), 'lng', ST_X(s.location::geometry),
                    'period_start', lower(wp.period), 'period_end', upper(wp.period) - 1,
                    'pm_employee_id', wp.pm_employee_id, 'pm_name', pm.full_name, 'pm_position', pm.position,
                    'leader_employee_id', wp.leader_employee_id, 'appeal_reason', wp.appeal_reason)
                  FROM vms.work_plan wp
                  LEFT JOIN vms.business_unit bu ON bu.id = wp.unit_id
                  LEFT JOIN vms.site s ON s.id = wp.site_id
                  LEFT JOIN vms.employee pm ON pm.id = wp.pm_employee_id
                  WHERE wp.id = :plan),
              'team', COALESCE((SELECT jsonb_agg(jsonb_build_object('employee_id', m.employee_id,
                            'full_name', e.full_name, 'position', e.position, 'role_in_plan', m.role_in_plan)
                            ORDER BY m.role_in_plan, e.full_name)
                        FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
                        WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)), '[]'::jsonb),
              'days', COALESCE((SELECT jsonb_agg(jsonb_build_object('id', d.id, 'work_date', d.work_date,
                            'title', d.title,
                            'tasks', (SELECT COALESCE(jsonb_agg(jsonb_build_object('id', t.id, 'title', t.title,
                                        'description', t.description,
                                        'files', (SELECT COALESCE(jsonb_agg(jsonb_build_object(
                                                    'file_id', f.id, 'file_name', f.file_name,
                                                    'mime_type', f.mime_type) ORDER BY ta.sort_order), '[]'::jsonb)
                                                  FROM vms.work_plan_task_attachment ta
                                                  JOIN vms.file_object f ON f.id = ta.file_id
                                                  WHERE ta.task_id = t.id))
                                        ORDER BY t.sort_order), '[]'::jsonb)
                                      FROM vms.work_plan_task t WHERE t.work_plan_day_id = d.id))
                            ORDER BY d.work_date)
                        FROM vms.work_plan_day d WHERE d.work_plan_id = :plan), '[]'::jsonb),
              'assets', COALESCE((SELECT jsonb_agg(jsonb_build_object('asset_id', a.id, 'kind', a.kind,
                            'vehicle_type', a.vehicle_type, 'code', a.code, 'name', a.name,
                            'driver_employee_id', al.driver_employee_id, 'driver_name', de.full_name)
                            ORDER BY a.kind, a.name)
                        FROM vms.asset_allocation al JOIN vms.asset a ON a.id = al.asset_id
                        LEFT JOIN vms.employee de ON de.id = al.driver_employee_id
                        WHERE al.work_plan_id = :plan AND al.released_at IS NULL), '[]'::jsonb)
            )
            """,
            {"plan": plan_id},
        )
