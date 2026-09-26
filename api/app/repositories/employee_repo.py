"""
app/repositories/employee_repo.py
Kueri karyawan untuk servis baru (V-29). Rute lama di api/employees.py belum dipindah ke sini.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base_repo import BaseRepo


class EmployeeRepo(BaseRepo):

    async def lock(self, employee_id: UUID | str, org_id: UUID | str) -> Any:
        return await self.fetchone(
            """
            SELECT id, deleted_at IS NOT NULL AS deleted, is_active, CAST(unit_id AS text) AS unit_id
            FROM vms.employee WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """,
            {"id": employee_id, "org": org_id},
        )

    async def restore(self, employee_id: UUID | str) -> None:
        """domain.js RESTORE_EMPLOYEE: data kembali sebagai NONAKTIF; akun tetap dicabut."""
        await self.execute(
            "UPDATE vms.employee SET deleted_at = NULL, is_active = false, updated_at = now() WHERE id = :id",
            {"id": employee_id})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})

    async def archive(self, employee_id: UUID | str) -> None:
        """Hapus lunak: tersembunyi dari daftar, data historis (SK, absensi, dokumen) tetap."""
        await self.execute(
            "UPDATE vms.employee SET deleted_at = now(), is_active = false, updated_at = now() WHERE id = :id",
            {"id": employee_id})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})

    async def assignments(self, employee_id: UUID | str, org_id: UUID | str) -> list[Any] | None:
        """Riwayat penempatan terbaru dulu. None bila karyawan bukan milik organisasi ini."""
        if not await self.scalar("SELECT 1 FROM vms.employee WHERE id = :id AND organization_id = :org",
                                 {"id": employee_id, "org": org_id}):
            return None
        return list(await self.fetchall(
            """
            SELECT a.id, a.employee_id, a.position, a.unit_id, u.name AS unit_name, a.valid_from, a.valid_to
            FROM vms.employee_assignment a LEFT JOIN vms.business_unit u ON u.id = a.unit_id
            WHERE a.employee_id = :id
            ORDER BY a.valid_from DESC, a.valid_to DESC NULLS FIRST
            """,
            {"id": employee_id}))

    async def last_assignment_start(self, employee_id: UUID | str) -> Any:
        return await self.scalar(
            "SELECT max(valid_from) FROM vms.employee_assignment WHERE employee_id = :id", {"id": employee_id})

    async def promote(self, employee_id: UUID | str, position: str, unit_id: str | None, valid_from: Any) -> Any:
        """Tutup penempatan terbuka pada tanggal mulai yang baru, buka yang baru, samakan data induk."""
        await self.execute(
            "UPDATE vms.employee_assignment SET valid_to = :start WHERE employee_id = :id AND valid_to IS NULL",
            {"id": employee_id, "start": valid_from})
        row = await self.fetchone(
            """
            INSERT INTO vms.employee_assignment (employee_id, position, unit_id, valid_from)
            VALUES (:id, :pos, :unit, :start)
            RETURNING id, employee_id, position, unit_id, valid_from, valid_to
            """,
            {"id": employee_id, "pos": position, "unit": unit_id, "start": valid_from})
        await self.execute(
            "UPDATE vms.employee SET position = :pos, unit_id = :unit, updated_at = now() WHERE id = :id",
            {"id": employee_id, "pos": position, "unit": unit_id})
        return row

    async def on_running_plan(self, employee_id: UUID | str) -> bool:
        """domain.js OFFBOARD: masih PM/ketua/anggota SK yang berjalan (bukan DRAFT/COMPLETED/CANCELLED)."""
        return bool(await self.scalar(
            """
            SELECT EXISTS (
                SELECT 1 FROM vms.work_plan wp
                WHERE wp.deleted_at IS NULL AND wp.status NOT IN ('DRAFT', 'COMPLETED', 'CANCELLED')
                  AND (wp.pm_employee_id = :emp OR wp.leader_employee_id = :emp
                       OR EXISTS (SELECT 1 FROM vms.work_plan_member m
                                  WHERE m.work_plan_id = wp.id AND m.employee_id = :emp
                                    AND upper_inf(m.valid_period))))
            """,
            {"emp": employee_id}))

    async def offboard(self, employee_id: UUID | str, reason: str, today: Any) -> None:
        """Masa kerja diakhiri: nonaktif, jabatan terbuka ditutup per hari ini, akun dicabut."""
        await self.execute(
            """
            UPDATE vms.employee SET is_active = false, offboarded_at = now(), offboarding_reason = :reason,
                   updated_at = now()
             WHERE id = :id
            """,
            {"id": employee_id, "reason": reason})
        await self.execute(
            """
            UPDATE vms.employee_assignment SET valid_to = GREATEST(valid_from, CAST(:today AS date))
             WHERE employee_id = :id AND valid_to IS NULL
            """,
            {"id": employee_id, "today": today})
        await self.execute("UPDATE vms.app_user SET is_active = false WHERE employee_id = :id", {"id": employee_id})
