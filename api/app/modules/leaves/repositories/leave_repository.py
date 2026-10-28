"""
app/modules/leaves/repositories/leave_repository.py

Repository untuk modul cuti & izin karyawan (leave_request & leave_balance).
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_LEAVE_SELECT = """
    SELECT lr.leave_id, lr.employee_id, e.full_name AS employee_name, e.employee_no,
           (SELECT f.id FROM file_object f WHERE f.storage_key = e.profile_photo_path LIMIT 1)
               AS employee_photo_file_id,
           d.name AS division_name, lr.leave_type::text AS leave_type, lr.start_date,
           lr.end_date, lr.total_days, lr.reason, lr.status::text AS status,
           lr.attachment_path,
           COALESCE(rev_hr.full_name, rev_pm.full_name) AS reviewed_by_name,
           lr.reviewed_at, lr.rejection_note, lr.create_at
    FROM leave_request lr
    JOIN employee e ON e.employee_id = lr.employee_id
    LEFT JOIN division d ON d.division_id = e.division_id
    LEFT JOIN employee rev_pm ON rev_pm.employee_id = lr.reviewed_by_pm_id
    LEFT JOIN employee rev_hr ON rev_hr.employee_id = lr.reviewed_by_hr_id
"""


class LeaveRepository(BaseRepository):
    """Query & transaksi basis data untuk leave_request dan leave_balance."""

    async def get_or_create_balance(self, employee_id: UUID | str, year: int, default_quota: int = 12) -> Any:
        """Ambil atau inisialisasi kuota cuti tahunan karyawan untuk tahun berjalan."""
        row = await self.fetchone(
            """
            SELECT balance_id, employee_id, period_year, total_quota, used_quota,
                   (total_quota - used_quota) AS remaining_quota
            FROM leave_balance
            WHERE employee_id = CAST(:emp AS uuid) AND period_year = :year AND delete_at IS NULL
            """,
            {"emp": str(employee_id), "year": year},
        )
        if row:
            return row

        await self.execute(
            """
            INSERT INTO leave_balance (employee_id, period_year, total_quota, used_quota)
            VALUES (CAST(:emp AS uuid), :year, :quota, 0)
            ON CONFLICT DO NOTHING
            """,
            {"emp": str(employee_id), "year": year, "quota": default_quota},
        )
        return await self.fetchone(
            """
            SELECT balance_id, employee_id, period_year, total_quota, used_quota,
                   (total_quota - used_quota) AS remaining_quota
            FROM leave_balance
            WHERE employee_id = CAST(:emp AS uuid) AND period_year = :year AND delete_at IS NULL
            """,
            {"emp": str(employee_id), "year": year},
        )

    async def deduct_balance(self, employee_id: UUID | str, year: int, days: int) -> bool:
        """
        Ubah used_quota secara atomik (satu UPDATE mengunci barisnya, jadi dua persetujuan bersamaan tidak
        melewati batas). Pemotongan (days > 0) ditolak bila sisa kuota kurang; pengembalian (days < 0) tidak
        pernah membuat used_quota negatif. Mengembalikan False bila tak ada baris yang berubah.
        """
        row = await self.fetchone(
            """
            UPDATE leave_balance
            SET used_quota = GREATEST(used_quota + :days, 0), update_at = now()
            WHERE employee_id = CAST(:emp AS uuid) AND period_year = :year AND delete_at IS NULL
              AND (:days <= 0 OR total_quota - used_quota >= :days)
            RETURNING balance_id
            """,
            {"emp": str(employee_id), "year": year, "days": days},
        )
        return row is not None

    async def has_overlapping_leave(
        self, employee_id: UUID | str, start_date: date, end_date: date
    ) -> bool:
        """Cek apakah karyawan sudah memiliki permohonan cuti aktif/pending yang bertabrakan tanggalnya."""
        sql = """
            SELECT 1
            FROM leave_request
            WHERE employee_id = CAST(:emp AS uuid)
              AND delete_at IS NULL
              AND status IN ('PENDING', 'APPROVED_BY_PM', 'APPROVED_BY_HR')
              AND start_date <= :end AND end_date >= :start
            LIMIT 1
        """
        val = await self.scalar(sql, {"emp": str(employee_id), "start": start_date, "end": end_date})
        return val is not None

    async def insert_leave(
        self,
        employee_id: UUID | str,
        leave_type: str,
        start_date: date,
        end_date: date,
        total_days: int,
        reason: str,
        attachment_path: str | None,
        status: str = "PENDING",
    ) -> UUID:
        """Membuat permohonan cuti baru."""
        leave_id: UUID = await self.scalar(
            """
            INSERT INTO leave_request (
                employee_id, leave_type, start_date, end_date, total_days,
                reason, attachment_path, status
            )
            VALUES (
                CAST(:emp AS uuid), CAST(:type AS leave_type_enum), :start, :end,
                :days, :reason, :attachment, CAST(:status AS approval_status_enum)
            )
            RETURNING leave_id
            """,
            {
                "emp": str(employee_id),
                "type": leave_type,
                "start": start_date,
                "end": end_date,
                "days": total_days,
                "reason": reason,
                "attachment": attachment_path,
                "status": status,
            },
        )
        return leave_id

    async def get_leave(self, leave_id: UUID | str, *, for_update: bool = False) -> Any:
        """Mengambil detail satu permohonan cuti; `for_update` mengunci barisnya sampai transaksi selesai."""
        return await self.fetchone(
            _LEAVE_SELECT + " WHERE lr.leave_id = CAST(:id AS uuid) AND lr.delete_at IS NULL"
            + (" FOR UPDATE OF lr" if for_update else ""),
            {"id": str(leave_id)},
        )

    async def list_leaves(
        self,
        *,
        employee_id: UUID | str | None = None,
        status: str | None = None,
        year: int | None = None,
        pm_id: UUID | str | None = None,
    ) -> Sequence[Any]:
        """Daftar permohonan cuti dengan filter (pm_id: hanya karyawan divisi PM tsb + dirinya)."""
        return await self.fetchall(
            _LEAVE_SELECT + """
            WHERE lr.delete_at IS NULL
              AND (CAST(:emp AS uuid) IS NULL OR lr.employee_id = CAST(:emp AS uuid))
              AND (CAST(:st AS text) IS NULL OR lr.status::text = :st)
              AND (CAST(:yr AS integer) IS NULL OR EXTRACT(YEAR FROM lr.start_date) = :yr)
              AND (CAST(:pm AS uuid) IS NULL OR d.pm_id = CAST(:pm AS uuid) OR lr.employee_id = CAST(:pm AS uuid))
            ORDER BY lr.create_at DESC
            """,
            {
                "emp": str(employee_id) if employee_id else None,
                "st": status,
                "yr": year,
                "pm": str(pm_id) if pm_id else None,
            },
        )

    async def division_pm_of(self, employee_id: UUID | str) -> Any:
        """pm_id divisi tempat karyawan bernaung (None bila tanpa divisi)."""
        row = await self.fetchone(
            """
            SELECT d.pm_id FROM employee e LEFT JOIN division d ON d.division_id = e.division_id
            WHERE e.employee_id = CAST(:id AS uuid)
            """,
            {"id": str(employee_id)},
        )
        return row.pm_id if row else None

    async def update_review(
        self,
        leave_id: UUID | str,
        status: str,
        reviewer_id: UUID | str,
        is_pm: bool,
        note: str | None,
    ) -> None:
        """Persetujuan atau penolakan cuti oleh PM atau HR."""
        pm_col = "reviewed_by_pm_id = CAST(:rev AS uuid)," if is_pm else ""
        hr_col = "reviewed_by_hr_id = CAST(:rev AS uuid)," if not is_pm else ""
        await self.execute(
            f"""
            UPDATE leave_request
            SET status = CAST(:st AS approval_status_enum),
                {pm_col}
                {hr_col}
                reviewed_at = now(),
                rejection_note = :note,
                update_at = now()
            WHERE leave_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(leave_id), "st": status, "rev": str(reviewer_id), "note": note},
        )

    async def cancel_leave(self, leave_id: UUID | str) -> None:
        """Pembatalan cuti oleh pemohon sendiri."""
        await self.execute(
            """
            UPDATE leave_request
            SET status = CAST('CANCELLED' AS approval_status_enum), update_at = now()
            WHERE leave_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(leave_id)},
        )
