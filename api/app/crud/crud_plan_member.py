"""
app/crud/crud_plan_member.py
Susunan tim pekerjaan (`work_plan_member`). Anggota aktif = `valid_period` terbuka
(sama dengan `vms.is_plan_member`); adendum personel kelak menutup baris, bukan menghapus.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any
from uuid import UUID

from app.core.enums import PlanStatus

from .base import CRUDBase


class CRUDPlanMember(CRUDBase):
    """
    CRUD untuk mengelola susunan anggota tim (personel) dalam sebuah rencana kerja (SK).
    Mengatur validasi periode aktif (valid_period), penguncian SK, dan manajemen konflik jadwal.
    """

    async def lock_plan(self, plan_id: UUID | str, org_id: UUID | str) -> Any:
        """
        Mengunci SK (FOR UPDATE) agar aman diubah tanpa race condition.
        
        Args:
            plan_id (UUID | str): ID rencana kerja (SK).
            org_id (UUID | str): ID organisasi.
            
        Returns:
            Any: Record SK yang terkunci (id, unit_id, status, row_version, dll), atau None jika tidak ditemukan.
        """
        # Mengunci baris (FOR UPDATE) SK yang akan diubah susunan timnya,
        # untuk mencegah modifikasi konkuren dari proses lain.
        return await self.fetchone(
            """
            SELECT id, unit_id, status, row_version, pm_employee_id, lower(period) AS period_start
            FROM vms.work_plan
            WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
            FOR UPDATE
            """,
            {"id": plan_id, "org": org_id},
        )

    async def active_team(self, plan_id: UUID | str) -> list[Any]:
        """
        Mengambil tim aktif dari sebuah SK. Ketua (LEADER) akan muncul paling atas.
        
        Args:
            plan_id (UUID | str): ID rencana kerja.
            
        Returns:
            list[Any]: Daftar anggota tim aktif beserta role (ketua/anggota).
        """
        # Mengambil anggota tim yang masih aktif (valid_period ujung atasnya masih infinity).
        # Menggunakan boolean casting (role_in_plan = 'LEADER') DESC agar ketua diurutkan di baris pertama.
        return list(await self.fetchall(
            """
            SELECT CAST(m.employee_id AS text) AS employee_id, CAST(m.role_in_plan AS text) AS role_in_plan,
                   e.full_name, e.position, lower(m.valid_period) AS valid_from
            FROM vms.work_plan_member m JOIN vms.employee e ON e.id = m.employee_id
            WHERE m.work_plan_id = :plan AND upper_inf(m.valid_period)
            ORDER BY (m.role_in_plan = 'LEADER') DESC, e.full_name
            """,
            {"plan": plan_id},
        ))

    async def active_employees(self, employee_ids: Iterable[UUID | str], org_id: UUID | str) -> set[str]:
        """
        Memvalidasi bahwa kumpulan ID karyawan yang diberikan adalah karyawan aktif di organisasi tersebut.
        
        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID karyawan.
            org_id (UUID | str): ID organisasi.
            
        Returns:
            set[str]: Himpunan ID karyawan yang valid dan aktif.
        """
        # Query untuk mengecek eksistensi dan status aktif karyawan.
        ids = [str(e) for e in employee_ids]
        rows = await self.fetchall(
            """
            SELECT id::text FROM vms.employee
            WHERE id = ANY(CAST(:ids AS uuid[])) AND organization_id = :org AND is_active AND deleted_at IS NULL
            """,
            {"ids": ids, "org": org_id},
        )
        return {r[0] for r in rows}

    async def schedule_conflicts(self, employee_ids: Iterable[UUID | str], plan_id: UUID | str) -> Sequence[Any]:
        """
        Mengecek bentrok jadwal: apakah ada karyawan yang sudah terikat di SK terbit lain
        pada periode yang sama.
        
        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID karyawan.
            plan_id (UUID | str): ID rencana kerja saat ini.
            
        Returns:
            Sequence[Any]: Daftar konflik yang mencakup employee_id, work_plan_id, number, dan title.
        """
        # Menggunakan CROSS JOIN LATERAL untuk memanggil fungsi vms.personnel_conflict bagi
        # setiap employee_id dalam list, membandingkan dengan periode SK saat ini.
        return await self.fetchall(
            """
            SELECT e.employee_id::text AS employee_id, c.work_plan_id::text AS work_plan_id, c.number, c.title
            FROM unnest(CAST(:ids AS uuid[])) AS e(employee_id)
            CROSS JOIN LATERAL vms.personnel_conflict(
                e.employee_id, (SELECT period FROM vms.work_plan WHERE id = :plan), :plan) AS c
            """,
            {"ids": [str(e) for e in employee_ids], "plan": plan_id},
        )

    async def schedule_conflicts_until(self, employee_ids: Iterable[UUID | str], plan_id: UUID | str,
                                       new_end: date) -> Sequence[Any]:
        """
        Mengecek bentrok jadwal untuk periode perpanjangan SK hingga tanggal `new_end`.
        
        Args:
            employee_ids (Iterable[UUID | str]): Kumpulan ID karyawan.
            plan_id (UUID | str): ID rencana kerja.
            new_end (date): Tanggal akhir baru perpanjangan.
            
        Returns:
            Sequence[Any]: Daftar konflik (employee_id, work_plan_id, number, title).
        """
        # Membuat daterange baru dari awal periode eksisting hingga `new_end` + 1 hari (interval eksklusif)
        # dan memanggil vms.personnel_conflict untuk mengecek bentrokan pada range tersebut.
        return await self.fetchall(
            """
            SELECT e.employee_id::text AS employee_id, c.work_plan_id::text AS work_plan_id, c.number, c.title
            FROM unnest(CAST(:ids AS uuid[])) AS e(employee_id)
            CROSS JOIN LATERAL vms.personnel_conflict(
                e.employee_id,
                (SELECT daterange(lower(period), CAST(:new_end AS date) + 1, '[)') FROM vms.work_plan WHERE id = :plan),
                :plan) AS c
            """,
            {"ids": [str(e) for e in employee_ids], "plan": plan_id, "new_end": new_end},
        )

    async def replace_team(
        self, plan_id: UUID | str, start: date, leader_id: UUID | str | None, member_ids: Sequence[UUID | str]
    ) -> None:
        """
        Mengganti seluruh susunan tim pada draf SK. Hanya boleh dipakai ketika SK masih draf,
        karena menghapus record (DELETE) alih-alih menutup `valid_period`.
        
        Args:
            plan_id (UUID | str): ID rencana kerja.
            start (date): Tanggal mulai anggota.
            leader_id (UUID | str | None): ID ketua (jika ada).
            member_ids (Sequence[UUID | str]): Daftar ID anggota.
        """
        # Menghapus seluruh baris work_plan_member lama, lalu
        # menyisipkan anggota tim yang baru menggunakan bulk insert dari array gabungan.
        await self.execute("DELETE FROM vms.work_plan_member WHERE work_plan_id = :plan", {"plan": plan_id})
        rows = ([(leader_id, "LEADER")] if leader_id else []) + [(m, "MEMBER") for m in member_ids]
        if rows:
            await self.execute(
                """
                INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period)
                SELECT :plan, CAST(u.emp AS uuid), CAST(u.role AS vms.role_code), daterange(CAST(:start AS date), NULL, '[)')
                FROM unnest(CAST(:emps AS text[]), CAST(:roles AS text[])) AS u(emp, role)
                """,
                {"plan": plan_id, "emps": [str(r[0]) for r in rows], "roles": [r[1] for r in rows], "start": start},
            )

    async def set_leader(self, plan_id: UUID | str, leader_id: UUID | str | None) -> int:
        """
        Menetapkan ketua pada master SK dan menaikkan versinya (row_version).
        
        Args:
            plan_id (UUID | str): ID rencana kerja.
            leader_id (UUID | str | None): ID ketua baru.
            
        Returns:
            int: Versi row terbaru (row_version).
        """
        # Memperbarui ketua pada work_plan dan mencegah edit konkuren dengan menaikkan row_version.
        return int(await self.scalar(
            """
            UPDATE vms.work_plan SET leader_employee_id = :leader, row_version = row_version + 1
            WHERE id = :plan AND status = :draft
            RETURNING row_version
            """,
            {"leader": leader_id, "plan": plan_id, "draft": PlanStatus.DRAFT},
        ))
