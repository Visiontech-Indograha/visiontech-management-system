"""Data pembuat SK dan cakupan unit personel (R-23)."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import UUID

from .base import CRUDBase


class CRUDPlanAssignment(CRUDBase):
    """
    Kelas CRUD untuk mengelola data pembuat SK dan penugasan/pencarian personel per unit kerja.
    """

    async def employee_of_user(self, user_id: UUID | str) -> Any:
        """Mengambil data ID pegawai dan ID unit bisnis dari pengguna.

        Args:
            user_id (UUID | str): ID pengguna aplikasi.

        Returns:
            Any: Baris data berisi employee_id dan unit_id.
        """
        # Melakukan JOIN antara vms.app_user dan vms.employee
        # dengan klausa WHERE memastikan employee dan user masih aktif (belum di-soft delete).
        return await self.fetchone(
            """
            SELECT e.id::text AS employee_id, e.unit_id::text AS unit_id
            FROM vms.app_user u
            JOIN vms.employee e ON e.id = u.employee_id
            WHERE u.id = :user AND e.is_active AND e.deleted_at IS NULL
            """,
            {"user": user_id},
        )

    async def employee_units(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> dict[str, str | None]:
        """Mengambil pemetaan ID unit untuk sejumlah pegawai dalam satu organisasi.

        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID pegawai.
            org_id (UUID | str): ID organisasi.

        Returns:
            dict[str, str | None]: Dictionary yang memetakan employee_id ke unit_id.
        """
        ids = [str(value) for value in employee_ids]
        # Menggunakan ANY(CAST(:ids AS uuid[])) untuk mengambil data sejumlah ID
        # sekaligus, menyaring yang masih aktif dan cocok dengan organization_id.
        rows = await self.fetchall(
            """
            SELECT id::text AS employee_id, unit_id::text AS unit_id
            FROM vms.employee
            WHERE id = ANY(CAST(:ids AS uuid[])) AND organization_id = :org
              AND is_active AND deleted_at IS NULL
            """,
            {"ids": ids, "org": org_id},
        )
        return {str(row.employee_id): str(row.unit_id) if row.unit_id else None for row in rows}

    async def active_project_managers(self, org_id: UUID | str) -> list[Any]:
        """Mengambil daftar Project Manager (PM) yang aktif di suatu organisasi.

        Args:
            org_id (UUID | str): ID organisasi.

        Returns:
            list[Any]: Daftar entri data Project Manager.
        """
        # Melakukan JOIN dari employee -> app_user -> user_role
        # dengan kondisi role = 'PM' untuk mendapatkan manajer proyek.
        # DISTINCT digunakan berjaga-jaga apabila ada duplikasi role yang belum tertangani.
        return list(await self.fetchall(
            """
            SELECT DISTINCT e.id, e.full_name, e.position, e.unit_id
            FROM vms.employee e
            JOIN vms.app_user u ON u.employee_id = e.id AND u.is_active
            JOIN vms.user_role ur ON ur.user_id = u.id AND ur.role = 'PM'
            WHERE e.organization_id = :org AND e.is_active AND e.deleted_at IS NULL
            ORDER BY e.full_name
            """,
            {"org": org_id},
        ))

    async def available_personnel(
        self,
        org_id: UUID | str,
        period_start: date,
        period_end: date,
        unit_id: UUID | str | None,
    ) -> list[Any]:
        """Mengambil data pegawai lapangan yang tersedia (tidak bentrok jadwal) untuk ditugaskan.

        Args:
            org_id (UUID | str): ID organisasi.
            period_start (date): Tanggal mulai periode SK.
            period_end (date): Tanggal akhir periode SK.
            unit_id (UUID | str | None): Filter opsional untuk spesifik ID unit bisnis.

        Returns:
            list[Any]: Daftar pegawai lapangan yang memenuhi kriteria.
        """
        # Melakukan verifikasi beberapa kriteria secara bersamaan:
        # 1. EXISTS untuk memastikan punya akun app_user aktif.
        # 2. NOT EXISTS untuk memastikan bukan user office (PM, OPS, dll).
        # 3. NOT EXISTS memanggil stored function vms.personnel_conflict untuk
        #    memastikan tidak ada konflik jadwal/penugasan pada rentang daterange tersebut.
        return list(await self.fetchall(
            """
            SELECT e.id, e.full_name, e.position, e.unit_id
            FROM vms.employee e
            WHERE e.organization_id = :org AND e.is_active AND e.deleted_at IS NULL
              AND EXISTS (
                  SELECT 1 FROM vms.app_user field_user
                  WHERE field_user.employee_id = e.id AND field_user.is_active
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM vms.app_user office_user
                  JOIN vms.user_role office_role ON office_role.user_id = office_user.id
                  WHERE office_user.employee_id = e.id AND office_user.is_active
                    AND office_role.role IN ('PM', 'OPS', 'ADMIN', 'HR', 'FINANCE', 'ASSET')
              )
              AND (CAST(:unit AS uuid) IS NULL OR e.unit_id = CAST(:unit AS uuid))
              AND NOT EXISTS (
                  SELECT 1 FROM vms.personnel_conflict(
                      e.id, daterange(CAST(:start AS date), CAST(:end AS date), '[]'), NULL
                  )
              )
            ORDER BY e.full_name
            """,
            {"org": org_id, "start": period_start, "end": period_end, "unit": unit_id},
        ))

    async def eligible_field_staff(
        self,
        employee_ids: Iterable[UUID | str],
        org_id: UUID | str,
    ) -> set[str]:
        """Menyaring kumpulan ID pegawai, mengembalikan hanya yang berstatus pegawai lapangan.

        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID pegawai yang akan dicek.
            org_id (UUID | str): ID organisasi.

        Returns:
            set[str]: Himpunan ID pegawai lapangan yang lolos validasi.
        """
        ids = [str(value) for value in employee_ids]
        if not ids:
            return set()
        # Logikanya serupa dengan available_personnel, bedanya query ini menggunakan = ANY(CAST(:ids))
        # tanpa melakukan validasi konflik waktu (hanya verifikasi tipe/peran field staff saja).
        rows = await self.fetchall(
            """
            SELECT e.id::text AS employee_id
            FROM vms.employee e
            WHERE e.id = ANY(CAST(:ids AS uuid[])) AND e.organization_id = :org
              AND e.is_active AND e.deleted_at IS NULL
              AND EXISTS (
                  SELECT 1 FROM vms.app_user field_user
                  WHERE field_user.employee_id = e.id AND field_user.is_active
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM vms.app_user office_user
                  JOIN vms.user_role office_role ON office_role.user_id = office_user.id
                  WHERE office_user.employee_id = e.id AND office_user.is_active
                    AND office_role.role IN ('PM', 'OPS', 'ADMIN', 'HR', 'FINANCE', 'ASSET')
              )
            """,
            {"ids": ids, "org": org_id},
        )
        return {str(row.employee_id) for row in rows}

