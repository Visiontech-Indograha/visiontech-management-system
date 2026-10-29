"""
app/modules/assets/repositories/asset_repository.py
Inventaris aset V2 (Master Schema V2).

Relasi: office/division 1─N tool & vehicle; vehicle 1─N vehicle_file, vehicle_inspection;
tool/vehicle 1─N asset_assignment N─1 employee, asset_assignment N─1 work_plan_daily (opsional).
Peminjaman berjalan = asset_assignment dengan `returned_at IS NULL` (dasar clearance offboarding).
Berkas/foto: kolom `*_path` = file_object.storage_key; `file_id` dikembalikan lewat join.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_WIB_TODAY = "(now() AT TIME ZONE 'Asia/Jakarta')::date"


def _wib_date(col: str) -> str:
    return f"({col} AT TIME ZONE 'Asia/Jakarta')::date"


# Peminjaman berjalan per aset: satu baris (aset tidak bisa dipinjam dua kali bersamaan).
_OPEN_LOAN = """
    LEFT JOIN LATERAL (
        SELECT aa.assignment_id, aa.employee_id AS holder_employee_id, he.full_name AS holder_name, aa.daily_plan_id
        FROM asset_assignment aa JOIN employee he ON he.employee_id = aa.employee_id
        WHERE aa.{col} = {alias}.{col} AND aa.returned_at IS NULL AND aa.delete_at IS NULL
        ORDER BY aa.loaned_at DESC LIMIT 1
    ) loan ON TRUE
"""

_TOOL_SELECT = f"""
    SELECT t.tool_id, t.office_id, o.name AS office_name, t.division_id, d.name AS division_name,
           t.ownership_type::text AS ownership_type, t.category::text AS category, t.name, t.tool_code,
           t.status::text AS status, fo.id AS photo_file_id,
           loan.assignment_id, loan.holder_employee_id, loan.holder_name, loan.daily_plan_id
    FROM tool t
    JOIN office o ON o.office_id = t.office_id
    LEFT JOIN division d ON d.division_id = t.division_id
    LEFT JOIN file_object fo ON fo.storage_key = t.photo_path
    {_OPEN_LOAN.format(col="tool_id", alias="t")}
"""

_VEHICLE_SELECT = f"""
    SELECT v.vehicle_id, v.office_id, o.name AS office_name, v.division_id, d.name AS division_name,
           v.vehicle_type::text AS vehicle_type, v.name, v.number_plate, v.status::text AS status,
           fo.id AS photo_file_id,
           (SELECT max({_wib_date("vf.expired_at")}) FROM vehicle_file vf
             WHERE vf.vehicle_id = v.vehicle_id AND vf.type = 'STNK' AND vf.status = 'active'
               AND vf.delete_at IS NULL) AS stnk_expired_at,
           (SELECT max({_wib_date("vf.expired_at")}) FROM vehicle_file vf
             WHERE vf.vehicle_id = v.vehicle_id AND vf.type = 'KIR' AND vf.status = 'active'
               AND vf.delete_at IS NULL) AS kir_expired_at,
           loan.assignment_id, loan.holder_employee_id, loan.holder_name, loan.daily_plan_id
    FROM vehicle v
    JOIN office o ON o.office_id = v.office_id
    JOIN division d ON d.division_id = v.division_id
    LEFT JOIN file_object fo ON fo.storage_key = v.photo_path
    {_OPEN_LOAN.format(col="vehicle_id", alias="v")}
"""

_LOAN_SELECT = """
    SELECT aa.assignment_id, aa.asset_type, COALESCE(aa.tool_id, aa.vehicle_id) AS asset_id,
           COALESCE(t.name, v.name) AS asset_name, COALESCE(t.tool_code, v.number_plate) AS asset_code,
           aa.employee_id, e.full_name AS employee_name,
           (SELECT f.id FROM file_object f WHERE f.storage_key = e.profile_photo_path LIMIT 1)
               AS employee_photo_file_id, aa.daily_plan_id, wpd.work_date,
           aa.assignment_status::text AS assignment_status, aa.loaned_at, aa.returned_at,
           fo.id AS handover_file_id, aa.return_requested_at, aa.return_condition, aa.return_note,
           rfo.id AS return_file_id
    FROM asset_assignment aa
    JOIN employee e ON e.employee_id = aa.employee_id
    LEFT JOIN tool t ON t.tool_id = aa.tool_id
    LEFT JOIN vehicle v ON v.vehicle_id = aa.vehicle_id
    LEFT JOIN work_plan_daily wpd ON wpd.daily_plan_id = aa.daily_plan_id
    LEFT JOIN file_object fo ON fo.storage_key = aa.handover_photo_path
    LEFT JOIN file_object rfo ON rfo.storage_key = aa.return_photo_path
"""

_REQUEST_SELECT = """
    SELECT r.request_id, r.asset_type, COALESCE(r.tool_id, r.vehicle_id) AS asset_id,
           COALESCE(t.name, v.name) AS asset_name, COALESCE(t.tool_code, v.number_plate) AS asset_code,
           r.employee_id, e.full_name AS employee_name,
           (SELECT f.id FROM file_object f WHERE f.storage_key = e.profile_photo_path LIMIT 1)
               AS employee_photo_file_id, r.purpose, r.needed_on, r.status, r.review_note,
           r.reviewed_at, r.assignment_id, r.create_at
    FROM asset_loan_request r
    JOIN employee e ON e.employee_id = r.employee_id
    LEFT JOIN tool t ON t.tool_id = r.tool_id
    LEFT JOIN vehicle v ON v.vehicle_id = r.vehicle_id
"""


class AssetRepository(BaseRepository):
    """Query tool, vehicle, vehicle_file, vehicle_inspection, asset_assignment."""

    # ── Rujukan ────────────────────────────────────────────────────────────────
    async def file_key(self, file_id: UUID | str) -> str | None:
        key: str | None = await self.scalar(
            "SELECT storage_key FROM file_object WHERE id = CAST(:id AS uuid)", {"id": str(file_id)}
        )
        return key

    async def office_exists(self, office_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM office WHERE office_id = CAST(:id AS uuid) AND delete_at IS NULL)",
            {"id": str(office_id)},
        ))

    async def division_active(self, division_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM division WHERE division_id = CAST(:id AS uuid) "
            "AND delete_at IS NULL AND status)",
            {"id": str(division_id)},
        ))

    async def employee_of_user(self, user_id: UUID | str) -> str | None:
        val = await self.scalar(
            "SELECT employee_id FROM users WHERE user_id = CAST(:uid AS uuid) AND delete_at IS NULL",
            {"uid": str(user_id)},
        )
        return str(val) if val else None

    async def employee_active(self, employee_id: UUID | str) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM employee WHERE employee_id = CAST(:id AS uuid) "
            "AND delete_at IS NULL AND offboarding_status = 'active')",
            {"id": str(employee_id)},
        ))

    async def valid_licences(self, employee_id: UUID | str) -> set[str]:
        """Jenis SIM karyawan yang berlaku hari ini (employee_file aktif, belum kedaluwarsa)."""
        rows = await self.fetchall(
            f"""
            SELECT DISTINCT type FROM employee_file
            WHERE employee_id = CAST(:id AS uuid) AND type LIKE 'SIM\\_%' AND status = 'active'
              AND delete_at IS NULL AND (expired_at IS NULL OR {_wib_date("expired_at")} >= {_WIB_TODAY})
            """,
            {"id": str(employee_id)},
        )
        return {r.type for r in rows}

    async def plan_for_loan(self, daily_plan_id: UUID | str, employee_id: UUID | str) -> Any:
        """Jadwal harian (belum dihapus) + apakah karyawan anggota aktif/ketua tim jadwal itu + apakah sudah lewat."""
        return await self.fetchone(
            f"""
            SELECT wpd.daily_plan_id, wpd.work_date, wpd.work_date < {_WIB_TODAY} AS is_past,
                   (t.leader_employee_id = CAST(:emp AS uuid)
                    OR EXISTS (SELECT 1 FROM member m
                               WHERE m.team_id = wpd.team_id AND m.employee_id = CAST(:emp AS uuid)
                                 AND m.is_active AND m.delete_at IS NULL)) AS on_team,
                   (d.pm_id = CAST(:emp AS uuid) OR d.om_id = CAST(:emp AS uuid)) AS manages
            FROM work_plan_daily wpd
            JOIN team t ON t.team_id = wpd.team_id
            JOIN division d ON d.division_id = wpd.division_id
            WHERE wpd.daily_plan_id = CAST(:id AS uuid) AND wpd.delete_at IS NULL
            """,
            {"id": str(daily_plan_id), "emp": str(employee_id)},
        )

    # ── Alat ───────────────────────────────────────────────────────────────────
    async def list_tools(self, office_id: UUID | None, status: str | None) -> list[Any]:
        return list(await self.fetchall(
            _TOOL_SELECT + """
            WHERE t.delete_at IS NULL
              AND (CAST(:office AS uuid) IS NULL OR t.office_id = CAST(:office AS uuid))
              AND (CAST(:status AS text) IS NULL OR t.status::text = :status)
            ORDER BY t.category, t.name
            """,
            {"office": str(office_id) if office_id else None, "status": status},
        ))

    async def get_tool(self, tool_id: UUID | str) -> Any:
        return await self.fetchone(
            _TOOL_SELECT + " WHERE t.tool_id = CAST(:id AS uuid) AND t.delete_at IS NULL", {"id": str(tool_id)}
        )

    async def tool_code_taken(self, code: str, exclude: UUID | str | None = None) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM tool WHERE upper(tool_code) = upper(:code) AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR tool_id <> CAST(:ex AS uuid)))",
            {"code": code, "ex": str(exclude) if exclude else None},
        ))

    async def insert_tool(self, fields: dict[str, Any]) -> UUID:
        tool_id: UUID = await self.scalar(
            """
            INSERT INTO tool (office_id, division_id, ownership_type, category, name, tool_code, photo_path)
            VALUES (CAST(:office_id AS uuid), CAST(:division_id AS uuid),
                    CAST(:ownership_type AS tool_ownership_enum), CAST(:category AS tool_category_enum),
                    :name, :tool_code, :photo_path)
            RETURNING tool_id
            """,
            fields,
        )
        return tool_id

    async def update_tool(self, tool_id: UUID | str, fields: dict[str, Any]) -> None:
        await self.execute(
            """
            UPDATE tool SET
                office_id = COALESCE(CAST(:office_id AS uuid), office_id),
                division_id = COALESCE(CAST(:division_id AS uuid), division_id),
                ownership_type = COALESCE(CAST(:ownership_type AS tool_ownership_enum), ownership_type),
                category = COALESCE(CAST(:category AS tool_category_enum), category),
                name = COALESCE(:name, name),
                tool_code = COALESCE(:tool_code, tool_code),
                photo_path = COALESCE(:photo_path, photo_path),
                update_at = now()
            WHERE tool_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {**fields, "id": str(tool_id)},
        )

    # ── Kendaraan ──────────────────────────────────────────────────────────────
    async def list_vehicles(self, office_id: UUID | None, status: str | None) -> list[Any]:
        return list(await self.fetchall(
            _VEHICLE_SELECT + """
            WHERE v.delete_at IS NULL
              AND (CAST(:office AS uuid) IS NULL OR v.office_id = CAST(:office AS uuid))
              AND (CAST(:status AS text) IS NULL OR v.status::text = :status)
            ORDER BY v.vehicle_type, v.name
            """,
            {"office": str(office_id) if office_id else None, "status": status},
        ))

    async def get_vehicle(self, vehicle_id: UUID | str) -> Any:
        return await self.fetchone(
            _VEHICLE_SELECT + " WHERE v.vehicle_id = CAST(:id AS uuid) AND v.delete_at IS NULL",
            {"id": str(vehicle_id)},
        )

    async def plate_taken(self, plate: str, exclude: UUID | str | None = None) -> bool:
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vehicle WHERE upper(number_plate) = upper(:plate) AND delete_at IS NULL "
            "AND (CAST(:ex AS uuid) IS NULL OR vehicle_id <> CAST(:ex AS uuid)))",
            {"plate": plate, "ex": str(exclude) if exclude else None},
        ))

    async def insert_vehicle(self, fields: dict[str, Any]) -> UUID:
        vehicle_id: UUID = await self.scalar(
            """
            INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate, photo_path)
            VALUES (CAST(:office_id AS uuid), CAST(:division_id AS uuid), CAST(:vehicle_type AS vehicle_type_enum),
                    :name, :number_plate, :photo_path)
            RETURNING vehicle_id
            """,
            fields,
        )
        return vehicle_id

    async def update_vehicle(self, vehicle_id: UUID | str, fields: dict[str, Any]) -> None:
        await self.execute(
            """
            UPDATE vehicle SET
                office_id = COALESCE(CAST(:office_id AS uuid), office_id),
                division_id = COALESCE(CAST(:division_id AS uuid), division_id),
                vehicle_type = COALESCE(CAST(:vehicle_type AS vehicle_type_enum), vehicle_type),
                name = COALESCE(:name, name),
                number_plate = COALESCE(:number_plate, number_plate),
                photo_path = COALESCE(:photo_path, photo_path),
                update_at = now()
            WHERE vehicle_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {**fields, "id": str(vehicle_id)},
        )

    # ── Status & arsip (tool / vehicle) ───────────────────────────────────────
    async def lock_asset(self, asset_type: str, asset_id: UUID | str) -> Any:
        """Kunci baris aset (FOR UPDATE) agar dua serah terima bersamaan tidak lolos."""
        table, col = ("tool", "tool_id") if asset_type == "TOOL" else ("vehicle", "vehicle_id")
        extra = ", ownership_type::text AS ownership_type" if asset_type == "TOOL" else \
            ", vehicle_type::text AS vehicle_type"
        return await self.fetchone(
            f"SELECT {col} AS asset_id, status::text AS status{extra} FROM {table} "
            f"WHERE {col} = CAST(:id AS uuid) AND delete_at IS NULL FOR UPDATE",
            {"id": str(asset_id)},
        )

    async def set_status(self, asset_type: str, asset_id: UUID | str, status: str) -> None:
        table, col = ("tool", "tool_id") if asset_type == "TOOL" else ("vehicle", "vehicle_id")
        await self.execute(
            f"UPDATE {table} SET status = CAST(:status AS asset_status_enum), update_at = now() "
            f"WHERE {col} = CAST(:id AS uuid)",
            {"id": str(asset_id), "status": status.lower()},
        )

    async def has_open_loan(self, asset_type: str, asset_id: UUID | str) -> bool:
        col = "tool_id" if asset_type == "TOOL" else "vehicle_id"
        return bool(await self.scalar(
            f"SELECT EXISTS (SELECT 1 FROM asset_assignment WHERE {col} = CAST(:id AS uuid) "
            "AND returned_at IS NULL AND delete_at IS NULL)",
            {"id": str(asset_id)},
        ))

    async def archive(self, asset_type: str, asset_id: UUID | str) -> None:
        table, col = ("tool", "tool_id") if asset_type == "TOOL" else ("vehicle", "vehicle_id")
        await self.execute(
            f"UPDATE {table} SET delete_at = now(), update_at = now() "
            f"WHERE {col} = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(asset_id)},
        )

    # ── Berkas kendaraan ──────────────────────────────────────────────────────
    async def vehicle_files(self, vehicle_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            f"""
            SELECT vf.vehicle_file_id, vf.vehicle_id, vf.type::text AS type, vf.status::text AS status,
                   {_wib_date("vf.active_at")} AS active_at, {_wib_date("vf.expired_at")} AS expired_at,
                   fo.id AS file_id, vf.create_at AS created_at
            FROM vehicle_file vf LEFT JOIN file_object fo ON fo.storage_key = vf.path_file
            WHERE vf.vehicle_id = CAST(:id AS uuid) AND vf.delete_at IS NULL
            ORDER BY (vf.status = 'active') DESC, vf.type, vf.active_at DESC
            """,
            {"id": str(vehicle_id)},
        ))

    async def insert_vehicle_file(
        self, vehicle_id: UUID | str, file_type: str, path: str, active_at: date | None, expired_at: date
    ) -> None:
        """Berkas sejenis yang baru menggantikan yang berlaku (lama → extended)."""
        await self.execute(
            "UPDATE vehicle_file SET status = 'extended', update_at = now() "
            "WHERE vehicle_id = CAST(:v AS uuid) AND type = CAST(:t AS vehicle_file_type_enum) "
            "AND status = 'active' AND delete_at IS NULL",
            {"v": str(vehicle_id), "t": file_type},
        )
        await self.execute(
            f"""
            INSERT INTO vehicle_file (vehicle_id, type, path_file, status, active_at, expired_at)
            VALUES (CAST(:v AS uuid), CAST(:t AS vehicle_file_type_enum), :path, 'active',
                    COALESCE(CAST(:active AS date), {_WIB_TODAY})::timestamp AT TIME ZONE 'Asia/Jakarta',
                    CAST(:expired AS date)::timestamp AT TIME ZONE 'Asia/Jakarta')
            """,
            {"v": str(vehicle_id), "t": file_type, "path": path, "active": active_at, "expired": expired_at},
        )

    # ── Inspeksi kendaraan ────────────────────────────────────────────────────
    async def inspections(self, vehicle_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT vi.vehicle_inspection_id, vi.vehicle_id, vi.type::text AS type, vi.inspector_employee_id,
                   e.full_name AS inspector_name, fo.id AS file_id, vi.create_at AS created_at
            FROM vehicle_inspection vi
            LEFT JOIN employee e ON e.employee_id = vi.inspector_employee_id
            LEFT JOIN file_object fo ON fo.storage_key = vi.path_file
            WHERE vi.vehicle_id = CAST(:id AS uuid) AND vi.delete_at IS NULL
            ORDER BY vi.create_at DESC
            """,
            {"id": str(vehicle_id)},
        ))

    async def insert_inspection(
        self, vehicle_id: UUID | str, inspector: str | None, inspection_type: str, path: str
    ) -> UUID:
        inspection_id: UUID = await self.scalar(
            """
            INSERT INTO vehicle_inspection (vehicle_id, inspector_employee_id, type, path_file)
            VALUES (CAST(:v AS uuid), CAST(:e AS uuid), CAST(:t AS inspection_type_enum), :path)
            RETURNING vehicle_inspection_id
            """,
            {"v": str(vehicle_id), "e": inspector, "t": inspection_type, "path": path},
        )
        return inspection_id

    # ── Peminjaman ────────────────────────────────────────────────────────────
    async def loans(
        self, *, open_only: bool, employee_id: UUID | str | None, daily_plan_id: UUID | str | None,
        managed_by: UUID | str | None,
    ) -> list[Any]:
        """`managed_by` (PM/OM): batasi ke pinjaman karyawan di divisi yang ia pimpin/kelola, atau miliknya sendiri."""
        return list(await self.fetchall(
            _LOAN_SELECT + """
            WHERE aa.delete_at IS NULL
              AND (NOT CAST(:open AS boolean) OR aa.returned_at IS NULL)
              AND (CAST(:emp AS uuid) IS NULL OR aa.employee_id = CAST(:emp AS uuid))
              AND (CAST(:plan AS uuid) IS NULL OR aa.daily_plan_id = CAST(:plan AS uuid))
              AND (CAST(:mgr AS uuid) IS NULL OR aa.employee_id = CAST(:mgr AS uuid)
                   OR aa.employee_id IN (
                       SELECT e.employee_id FROM employee e JOIN division d ON d.division_id = e.division_id
                       WHERE d.pm_id = CAST(:mgr AS uuid) OR d.om_id = CAST(:mgr AS uuid)))
            ORDER BY aa.returned_at IS NULL DESC, aa.loaned_at DESC
            """,
            {"open": open_only, "emp": str(employee_id) if employee_id else None,
             "plan": str(daily_plan_id) if daily_plan_id else None,
             "mgr": str(managed_by) if managed_by else None},
        ))

    async def get_loan(self, assignment_id: UUID | str) -> Any:
        return await self.fetchone(
            _LOAN_SELECT + " WHERE aa.assignment_id = CAST(:id AS uuid) AND aa.delete_at IS NULL",
            {"id": str(assignment_id)},
        )

    async def open_loan_for_update(self, assignment_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT assignment_id, asset_type, COALESCE(tool_id, vehicle_id) AS asset_id FROM asset_assignment "
            "WHERE assignment_id = CAST(:id AS uuid) AND returned_at IS NULL AND delete_at IS NULL FOR UPDATE",
            {"id": str(assignment_id)},
        )

    async def insert_loan(
        self,
        asset_type: str,
        asset_id: UUID | str,
        employee_id: UUID | str,
        daily_plan_id: UUID | str | None,
        status: str,
        handover_path: str | None,
    ) -> UUID:
        col = "tool_id" if asset_type == "TOOL" else "vehicle_id"
        assignment_id: UUID = await self.scalar(
            f"""
            INSERT INTO asset_assignment (asset_type, {col}, employee_id, daily_plan_id, assignment_status,
                                          handover_photo_path)
            VALUES (:type, CAST(:asset AS uuid), CAST(:emp AS uuid), CAST(:plan AS uuid),
                    CAST(:status AS asset_status_enum), :photo)
            RETURNING assignment_id
            """,
            {"type": asset_type, "asset": str(asset_id), "emp": str(employee_id),
             "plan": str(daily_plan_id) if daily_plan_id else None, "status": status.lower(), "photo": handover_path},
        )
        return assignment_id

    async def close_loan(self, assignment_id: UUID | str, condition: str) -> None:
        await self.execute(
            "UPDATE asset_assignment SET returned_at = now(), assignment_status = CAST(:c AS asset_status_enum), "
            "update_at = now() WHERE assignment_id = CAST(:id AS uuid)",
            {"id": str(assignment_id), "c": condition.lower()},
        )

    # ── Pengajuan pinjam & pengembalian oleh karyawan ──────────────────────────
    async def insert_request(
        self, asset_type: str, asset_id: UUID | str, employee_id: UUID | str, purpose: str, needed_on: date | None
    ) -> UUID:
        col = "tool_id" if asset_type == "TOOL" else "vehicle_id"
        request_id: UUID = await self.scalar(
            f"""
            INSERT INTO asset_loan_request (asset_type, {col}, employee_id, purpose, needed_on)
            VALUES (:type, CAST(:asset AS uuid), CAST(:emp AS uuid), :purpose, CAST(:needed AS date))
            RETURNING request_id
            """,
            {"type": asset_type, "asset": str(asset_id), "emp": str(employee_id), "purpose": purpose,
             "needed": needed_on},
        )
        return request_id

    async def has_pending_request(self, asset_type: str, asset_id: UUID | str, employee_id: UUID | str) -> bool:
        col = "tool_id" if asset_type == "TOOL" else "vehicle_id"
        return bool(await self.scalar(
            f"SELECT EXISTS (SELECT 1 FROM asset_loan_request WHERE {col} = CAST(:a AS uuid) "
            "AND employee_id = CAST(:e AS uuid) AND status = 'PENDING' AND delete_at IS NULL)",
            {"a": str(asset_id), "e": str(employee_id)},
        ))

    async def requests(self, *, employee_id: UUID | str | None, status: str | None) -> list[Any]:
        return list(await self.fetchall(
            _REQUEST_SELECT + """
            WHERE r.delete_at IS NULL
              AND (CAST(:emp AS uuid) IS NULL OR r.employee_id = CAST(:emp AS uuid))
              AND (CAST(:st AS text) IS NULL OR r.status = CAST(:st AS text))
            ORDER BY (r.status = 'PENDING') DESC, r.create_at DESC
            """,
            {"emp": str(employee_id) if employee_id else None, "st": status},
        ))

    async def get_request(self, request_id: UUID | str) -> Any:
        return await self.fetchone(
            _REQUEST_SELECT + " WHERE r.request_id = CAST(:id AS uuid) AND r.delete_at IS NULL",
            {"id": str(request_id)},
        )

    async def request_for_update(self, request_id: UUID | str) -> Any:
        return await self.fetchone(
            "SELECT request_id, asset_type, tool_id, vehicle_id, employee_id, status FROM asset_loan_request "
            "WHERE request_id = CAST(:id AS uuid) AND delete_at IS NULL FOR UPDATE",
            {"id": str(request_id)},
        )

    async def set_request_status(
        self, request_id: UUID | str, status: str, reviewer: str | None, note: str | None,
        assignment_id: UUID | str | None = None,
    ) -> None:
        await self.execute(
            "UPDATE asset_loan_request SET status = :st, reviewed_by_id = CAST(:rev AS uuid), reviewed_at = now(), "
            "review_note = :note, assignment_id = CAST(:asg AS uuid), update_at = now() "
            "WHERE request_id = CAST(:id AS uuid)",
            {"id": str(request_id), "st": status, "rev": reviewer, "note": note,
             "asg": str(assignment_id) if assignment_id else None},
        )

    async def request_return(
        self, assignment_id: UUID | str, condition: str, note: str | None, photo_path: str
    ) -> None:
        await self.execute(
            "UPDATE asset_assignment SET return_requested_at = now(), return_condition = :c, return_note = :n, "
            "return_photo_path = :p, update_at = now() WHERE assignment_id = CAST(:id AS uuid)",
            {"id": str(assignment_id), "c": condition, "n": note, "p": photo_path},
        )
