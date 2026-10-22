"""
app/modules/offboarding/repositories/offboarding_repository.py
Offboarding (Milestone 9, docs/35 §7).

Relasi: employee 1─N employee_offboarding (satu yang terbuka) 1─N offboarding_clearance_item N─1 asset_assignment
(pinjaman yang belum kembali saat offboarding dibuat). Penyetuju PM/HR = employee.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_COLS = """
    o.offboarding_id, o.employee_id, o.reason_type::text AS reason_type, o.submission_date, o.effective_date,
    o.is_all_assets_returned, o.status, o.notes, o.create_at,
    o.approved_by_pm_id, pm.full_name AS approved_by_pm_name, o.approved_by_hr_id, hr.full_name AS approved_by_hr_name,
    e.full_name AS employee_name, e.employee_no, e.division_id, d.name AS division_name,
    (SELECT COUNT(*) FROM offboarding_clearance_item c
     WHERE c.offboarding_id = o.offboarding_id AND c.verified_at IS NULL AND c.delete_at IS NULL)::int AS pending_items
"""
_FROM = """
    FROM employee_offboarding o
    JOIN employee e ON e.employee_id = o.employee_id
    LEFT JOIN division d ON d.division_id = e.division_id
    LEFT JOIN employee pm ON pm.employee_id = o.approved_by_pm_id
    LEFT JOIN employee hr ON hr.employee_id = o.approved_by_hr_id
"""


class OffboardingRepository(BaseRepository):
    async def list_all(self, *, status: str | None, division_id: UUID | str | None) -> list[Any]:
        return list(await self.fetchall(
            f"""
            SELECT {_COLS} {_FROM}
            WHERE o.delete_at IS NULL
              AND (CAST(:status AS varchar) IS NULL OR o.status = CAST(:status AS varchar))
              AND (CAST(:div AS uuid) IS NULL OR e.division_id = CAST(:div AS uuid))
            ORDER BY (o.status = 'COMPLETED'), o.effective_date, o.submission_date DESC
            """,
            {"status": status, "div": str(division_id) if division_id else None},
        ))

    async def get(self, offboarding_id: UUID | str, *, for_update: bool = False) -> Any:
        lock = " FOR UPDATE OF o" if for_update else ""
        return await self.fetchone(
            f"SELECT {_COLS} {_FROM} WHERE o.offboarding_id = CAST(:id AS uuid) AND o.delete_at IS NULL{lock}",
            {"id": str(offboarding_id)},
        )

    async def items(self, offboarding_id: UUID | str) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT c.clearance_item_id, c.offboarding_id, c.assignment_id, c.return_condition, c.handover_photo_path,
                   c.verified_by_id, v.full_name AS verified_by_name, c.verified_at,
                   a.asset_type, a.loaned_at, COALESCE(t.name, vh.name) AS asset_name,
                   COALESCE(t.tool_code, vh.number_plate) AS asset_code
            FROM offboarding_clearance_item c
            JOIN asset_assignment a ON a.assignment_id = c.assignment_id
            LEFT JOIN tool t ON t.tool_id = a.tool_id
            LEFT JOIN vehicle vh ON vh.vehicle_id = a.vehicle_id
            LEFT JOIN employee v ON v.employee_id = c.verified_by_id
            WHERE c.offboarding_id = CAST(:id AS uuid) AND c.delete_at IS NULL
            ORDER BY a.loaned_at
            """,
            {"id": str(offboarding_id)},
        ))

    async def employee_for_offboarding(self, employee_id: UUID | str) -> Any:
        """Karyawan + kedudukan yang harus diserahterimakan dulu (ketua tim aktif, PM/OM divisi)."""
        return await self.fetchone(
            """
            SELECT e.employee_id, e.full_name, e.offboarding_status::text AS offboarding_status, e.division_id,
                   (e.join_date AT TIME ZONE 'Asia/Jakarta')::date AS join_date,
                   (e.pkwt_end_date AT TIME ZONE 'Asia/Jakarta')::date AS pkwt_end_date,
                   (SELECT string_agg(t.name, ', ') FROM team t
                    WHERE t.leader_employee_id = e.employee_id AND t.status AND t.delete_at IS NULL) AS leads_teams,
                   (SELECT string_agg(dv.name, ', ') FROM division dv
                    WHERE e.employee_id IN (dv.pm_id, dv.om_id) AND dv.delete_at IS NULL) AS manages_divisions
            FROM employee e
            WHERE e.employee_id = CAST(:id AS uuid) AND e.delete_at IS NULL
            """,
            {"id": str(employee_id)},
        )

    async def open_for_employee(self, employee_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT offboarding_id FROM employee_offboarding WHERE employee_id = CAST(:id AS uuid) "
            "AND delete_at IS NULL AND status <> 'COMPLETED'",
            {"id": str(employee_id)},
        )

    async def create(self, *, employee_id: UUID | str, reason: str, effective_date: date, notes: str | None) -> Any:
        """Buat offboarding + item clearance dari pinjaman yang belum kembali; karyawan → in_process."""
        offboarding_id = await self.scalar(
            """
            INSERT INTO employee_offboarding (employee_id, reason_type, effective_date, status, notes)
            VALUES (CAST(:emp AS uuid), CAST(:reason AS offboarding_reason_enum), :eff, 'CLEARANCE_PENDING', :notes)
            RETURNING offboarding_id
            """,
            {"emp": str(employee_id), "reason": reason, "eff": effective_date, "notes": notes},
        )
        await self.execute(
            """
            INSERT INTO offboarding_clearance_item (offboarding_id, assignment_id, return_condition)
            SELECT CAST(:oid AS uuid), a.assignment_id, 'PENDING'
            FROM asset_assignment a
            WHERE a.employee_id = CAST(:emp AS uuid) AND a.returned_at IS NULL AND a.delete_at IS NULL
            """,
            {"oid": str(offboarding_id), "emp": str(employee_id)},
        )
        await self.refresh_clearance(offboarding_id)
        await self.execute(
            "UPDATE employee SET offboarding_status = 'in_process', update_at = now() "
            "WHERE employee_id = CAST(:emp AS uuid)",
            {"emp": str(employee_id)},
        )
        return offboarding_id

    async def refresh_clearance(self, offboarding_id: UUID | str) -> None:
        """is_all_assets_returned & status mengikuti item yang belum diverifikasi (CLEARANCE_PENDING ↔ SUBMITTED)."""
        await self.execute(
            """
            UPDATE employee_offboarding o
            SET is_all_assets_returned = NOT p.pending,
                status = CASE WHEN o.status IN ('CLEARANCE_PENDING', 'SUBMITTED')
                              THEN CASE WHEN p.pending THEN 'CLEARANCE_PENDING' ELSE 'SUBMITTED' END
                              ELSE o.status END,
                update_at = now()
            FROM (SELECT EXISTS (SELECT 1 FROM offboarding_clearance_item c
                                 WHERE c.offboarding_id = CAST(:id AS uuid) AND c.verified_at IS NULL
                                   AND c.delete_at IS NULL) AS pending) p
            WHERE o.offboarding_id = CAST(:id AS uuid)
            """,
            {"id": str(offboarding_id)},
        )

    async def item_for_update(self, clearance_item_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT c.clearance_item_id, c.offboarding_id, c.assignment_id, c.verified_at, o.status,
                   a.returned_at, e.division_id
            FROM offboarding_clearance_item c
            JOIN employee_offboarding o ON o.offboarding_id = c.offboarding_id AND o.delete_at IS NULL
            JOIN asset_assignment a ON a.assignment_id = c.assignment_id
            JOIN employee e ON e.employee_id = o.employee_id
            WHERE c.clearance_item_id = CAST(:id AS uuid) AND c.delete_at IS NULL
            FOR UPDATE OF c
            """,
            {"id": str(clearance_item_id)},
        )

    async def verify_item(self, clearance_item_id: UUID | str, condition: str, photo_path: str | None,
                          verifier_id: UUID | str) -> None:
        await self.execute(
            """
            UPDATE offboarding_clearance_item
            SET return_condition = :cond, handover_photo_path = :photo, verified_by_id = CAST(:by AS uuid),
                verified_at = now(), update_at = now()
            WHERE clearance_item_id = CAST(:id AS uuid)
            """,
            {"id": str(clearance_item_id), "cond": condition, "photo": photo_path, "by": str(verifier_id)},
        )

    async def file_key(self, file_id: UUID | str) -> str | None:
        key: str | None = await self.scalar(
            "SELECT storage_key FROM file_object WHERE id = CAST(:id AS uuid) AND mime_type LIKE 'image/%'",
            {"id": str(file_id)},
        )
        return key

    async def division_managers(self, division_id: UUID | str | None) -> Any:
        if division_id is None:
            return None
        return await self.fetchone(
            "SELECT pm_id, om_id FROM division WHERE division_id = CAST(:id AS uuid) AND delete_at IS NULL",
            {"id": str(division_id)},
        )

    async def approve(self, offboarding_id: UUID | str, *, as_pm: bool, approver_id: UUID | str) -> None:
        column = "approved_by_pm_id" if as_pm else "approved_by_hr_id"
        await self.execute(
            f"""
            UPDATE employee_offboarding
            SET {column} = CAST(:by AS uuid),
                status = CASE WHEN {'approved_by_hr_id' if as_pm else 'approved_by_pm_id'} IS NOT NULL
                              THEN 'APPROVED' ELSE status END,
                update_at = now()
            WHERE offboarding_id = CAST(:id AS uuid)
            """,
            {"id": str(offboarding_id), "by": str(approver_id)},
        )

    async def finalize(self, offboarding_id: UUID | str, employee_id: UUID | str) -> None:
        """COMPLETED: karyawan offboarded, keanggotaan tim berakhir, akun dinonaktifkan & semua sesi dicabut."""
        params = {"id": str(offboarding_id), "emp": str(employee_id)}
        await self.execute(
            "UPDATE employee_offboarding SET status = 'COMPLETED', update_at = now() "
            "WHERE offboarding_id = CAST(:id AS uuid)", params)
        await self.execute(
            "UPDATE employee SET offboarding_status = 'offboarded', update_at = now() "
            "WHERE employee_id = CAST(:emp AS uuid)", params)
        await self.execute(
            "UPDATE member SET is_active = FALSE, update_at = now() "
            "WHERE employee_id = CAST(:emp AS uuid) AND is_active", params)
        await self.execute(
            """
            UPDATE user_sessions SET is_revoked = TRUE, update_at = now()
            WHERE user_id IN (SELECT user_id FROM users WHERE employee_id = CAST(:emp AS uuid)) AND NOT is_revoked
            """, params)
        await self.execute(
            "UPDATE users SET is_active = FALSE, update_at = now() WHERE employee_id = CAST(:emp AS uuid)", params)

    async def due_for_completion(self, today: date) -> list[Any]:
        return list(await self.fetchall(
            "SELECT offboarding_id, employee_id FROM employee_offboarding "
            "WHERE status = 'APPROVED' AND effective_date <= :today AND delete_at IS NULL",
            {"today": today},
        ))

    async def cancel(self, offboarding_id: UUID | str, employee_id: UUID | str, note: str) -> None:
        """Batal (sebelum COMPLETED): item belum diverifikasi dibuang, catatan disimpan, karyawan aktif kembali."""
        params = {"id": str(offboarding_id), "emp": str(employee_id), "note": note}
        await self.execute(
            "UPDATE offboarding_clearance_item SET delete_at = now(), update_at = now() "
            "WHERE offboarding_id = CAST(:id AS uuid) AND verified_at IS NULL AND delete_at IS NULL", params)
        await self.execute(
            """
            UPDATE employee_offboarding
            SET delete_at = now(), update_at = now(),
                notes = concat_ws(E'\\n', notes, '[Dibatalkan] ' || CAST(:note AS text))
            WHERE offboarding_id = CAST(:id AS uuid)
            """, params)
        await self.execute(
            "UPDATE employee SET offboarding_status = 'active', update_at = now() "
            "WHERE employee_id = CAST(:emp AS uuid) AND offboarding_status = 'in_process'", params)

    async def pkwt_expiring(self, until: date, division_id: UUID | str | None) -> list[Any]:
        return list(await self.fetchall(
            """
            SELECT e.employee_id, e.employee_no, e.full_name, d.name AS division_name,
                   (e.pkwt_end_date AT TIME ZONE 'Asia/Jakarta')::date AS pkwt_end_date,
                   (SELECT COUNT(*) FROM asset_assignment a WHERE a.employee_id = e.employee_id
                    AND a.returned_at IS NULL AND a.delete_at IS NULL)::int AS open_loans
            FROM employee e
            LEFT JOIN division d ON d.division_id = e.division_id
            WHERE e.delete_at IS NULL AND e.offboarding_status = 'active' AND e.pkwt_end_date IS NOT NULL
              AND (e.pkwt_end_date AT TIME ZONE 'Asia/Jakarta')::date <= :until
              AND (CAST(:div AS uuid) IS NULL OR e.division_id = CAST(:div AS uuid))
            ORDER BY e.pkwt_end_date, e.full_name
            """,
            {"until": until, "div": str(division_id) if division_id else None},
        ))
