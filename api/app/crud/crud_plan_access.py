"""
app/crud/crud_plan_access.py
Kedudukan pengguna terhadap SK (V-07): siapa yang boleh melihat dan mengelola, dan apakah ia ketua
atau anggota menurut SK yang berlaku. Satu kueri dipakai penjaga `plan_access` dan daftar SK agar
aturan "terlihat" hanya ditulis sekali.

Terlihat (`domain.js` visiblePlans; `db/03` work_plan_visibility):
- ADMIN, OPS — semua SK organisasi;
- PM — SK unitnya (termasuk draf);
- ketua/anggota menurut SK, ASSET — SK yang sudah terbit (bukan DRAFT).
Mengelola (kewenangan PM) = ADMIN, OPS (`domain.js` permissions.OPS), atau PM unit SK itu.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from .base import CRUDBase

# `:plan` NULL → semua SK terlihat (daftar); terisi → satu SK (penjaga). `:status` NULL → semua status.
_STANDING = """
    SELECT id, unit_id, site_id, number, title, location_text, description, period_start, period_end, status, pm_employee_id, leader_employee_id, revision, row_version, cancellation_reason, appeal_reason, category, pending_request, created_at, manages, is_leader, is_member, visible FROM (
        SELECT wp.id, wp.unit_id, wp.site_id, wp.number, wp.title, wp.location_text, wp.description,
               lower(wp.period) AS period_start, upper(wp.period) - 1 AS period_end,
               wp.status, wp.pm_employee_id, wp.leader_employee_id, wp.revision, wp.row_version,
               wp.cancellation_reason, wp.appeal_reason, wp.category, wp.created_at,
               -- T2: ada permintaan revisi/adendum dari ketua yang menunggu PM.
               (wp.status = 'APPEALED' OR EXISTS (SELECT 1 FROM vms.plan_change pc
                  WHERE pc.work_plan_id = wp.id AND pc.status = 'PENDING_PM')) AS pending_request,
               s.oversees OR s.pm_of_unit AS manages,
               s.is_leader, s.is_member,
               -- Draf terarsip hanya terlihat oleh pengelola (domain.js visiblePlans includeArchived, V-21).
               CASE WHEN wp.deleted_at IS NOT NULL THEN s.oversees OR s.pm_of_unit
                    ELSE s.oversees OR s.pm_of_unit
                         OR (wp.status <> 'DRAFT' AND (s.asset_officer OR s.is_leader OR s.is_member))
               END AS visible
        FROM vms.work_plan wp
        CROSS JOIN LATERAL (
            SELECT
                EXISTS (SELECT 1 FROM vms.user_role ur
                        WHERE ur.user_id = CAST(:user AS uuid) AND ur.role IN ('ADMIN', 'OPS')) AS oversees,
                EXISTS (SELECT 1 FROM vms.user_role ur
                        WHERE ur.user_id = CAST(:user AS uuid) AND ur.role = 'PM'
                          AND (ur.unit_id IS NULL OR ur.unit_id = wp.unit_id)) AS pm_of_unit,
                EXISTS (SELECT 1 FROM vms.user_role ur
                        WHERE ur.user_id = CAST(:user AS uuid) AND ur.role = 'ASSET') AS asset_officer,
                vms.is_plan_leader(wp.id, CAST(:user AS uuid)) AS is_leader,
                vms.is_plan_member(wp.id, CAST(:user AS uuid)) AS is_member
        ) AS s
        WHERE wp.organization_id = CAST(:org AS uuid)
          AND (CAST(:archived AS boolean) IS NULL OR (wp.deleted_at IS NOT NULL) = CAST(:archived AS boolean))
          AND (CAST(:plan AS uuid) IS NULL OR wp.id = CAST(:plan AS uuid))
          AND (CAST(:status AS text) IS NULL OR CAST(wp.status AS text) = CAST(:status AS text))
    ) AS standing
    WHERE standing.visible
    ORDER BY standing.created_at DESC
"""


class CRUDPlanAccess(CRUDBase):
    """
    Kelas CRUD untuk mengelola dan memverifikasi akses pengguna terhadap Work Plan (SK).
    """

    async def standing(self, plan_id: UUID | str, org_id: UUID | str, user_id: UUID | str,
                       archived: bool | None = False) -> Any:
        """Baris SK + kedudukan pengguna; None bila SK tidak ada, milik organisasi lain, atau tak terlihat.
        `archived`: False = aktif saja, True = terarsip saja, None = keduanya (pemulihan).

        Args:
            plan_id (UUID | str): ID Work Plan.
            org_id (UUID | str): ID organisasi pengguna.
            user_id (UUID | str): ID pengguna.
            archived (bool | None, optional): Filter untuk status arsip. Default: False.

        Returns:
            Any: Baris data berisi detail SK dan hak akses pengguna (manages, is_leader, is_member, visible).
        """
        # Menjalankan kueri _STANDING yang menggunakan CROSS JOIN LATERAL untuk mengevaluasi
        # peran pengguna terhadap SK tersebut (ADMIN, OPS, PM, ASSET, LEADER, MEMBER)
        # dan menentukan visibilitas berdasarkan status SK (draft/aktif) serta deleted_at.
        return await self.fetchone(_STANDING, {"plan": str(plan_id), "org": org_id, "user": user_id,
                                               "status": None, "archived": archived})

    async def visible_plans(self, org_id: UUID | str, user_id: UUID | str, status: str | None,
                            archived: bool = False) -> Sequence[Any]:
        """Daftar semua SK yang dapat dilihat oleh pengguna di organisasinya.

        Args:
            org_id (UUID | str): ID organisasi.
            user_id (UUID | str): ID pengguna.
            status (str | None): Filter status SK.
            archived (bool, optional): Jika True, hanya ambil SK yang diarsipkan. Default: False.

        Returns:
            Sequence[Any]: Daftar SK yang dapat diakses pengguna.
        """
        # Mengeksekusi kueri _STANDING yang sama tanpa memfilter ID SK tertentu,
        # sehingga mengembalikan seluruh SK yang 'visible' bagi pengguna.
        return await self.fetchall(_STANDING, {"plan": None, "org": org_id, "user": user_id,
                                               "status": status, "archived": archived})

    async def plan_of_day(self, day_id: UUID | str) -> Any:
        """Mendapatkan ID Work Plan berdasarkan ID harinya.

        Args:
            day_id (UUID | str): ID dari work_plan_day.

        Returns:
            Any: ID dari work_plan terkait.
        """
        # Melakukan seleksi sederhana pada tabel vms.work_plan_day.
        return await self.scalar("SELECT work_plan_id FROM vms.work_plan_day WHERE id = :day", {"day": day_id})

    async def plan_of_allocation(self, allocation_id: UUID | str) -> Any:
        """Mendapatkan ID Work Plan berdasarkan ID alokasi aset.

        Args:
            allocation_id (UUID | str): ID dari asset_allocation.

        Returns:
            Any: ID dari work_plan terkait.
        """
        # Melakukan seleksi sederhana pada tabel vms.asset_allocation.
        return await self.scalar(
            "SELECT work_plan_id FROM vms.asset_allocation WHERE id = :alloc", {"alloc": allocation_id})

    async def plan_of_incident(self, incident_id: UUID | str, org_id: UUID | str) -> Any:
        """Mendapatkan ID Work Plan berdasarkan ID laporan insiden.

        Args:
            incident_id (UUID | str): ID dari incident_report.
            org_id (UUID | str): ID organisasi untuk validasi kepemilikan.

        Returns:
            Any: ID dari work_plan terkait.
        """
        # Mengambil work_plan_id dari tabel vms.incident_report sambil
        # memvalidasi agar tidak salah akses data antar organisasi (tenant isolation).
        return await self.scalar(
            "SELECT work_plan_id FROM vms.incident_report WHERE id = :inc AND organization_id = CAST(:org AS uuid)",
            {"inc": incident_id, "org": org_id})

    async def unit_standing(self, unit_id: UUID | str, org_id: UUID | str, user_id: UUID | str) -> Any:
        """(ada di organisasi ini?, boleh dikelola pengguna?) — untuk membuat SK di sebuah unit.

        Args:
            unit_id (UUID | str): ID unit bisnis target.
            org_id (UUID | str): ID organisasi pengguna.
            user_id (UUID | str): ID pengguna (app_user).

        Returns:
            Any: Baris dengan field 'manages' (Boolean) jika pengguna berhak mengelola unit.
        """
        # Memeriksa peran pengguna (vms.user_role) apakah ia adalah ADMIN/OPS,
        # atau PM pada unit bisnis tersebut. Jika ya, subquery EXISTS bernilai TRUE (manages).
        return await self.fetchone(
            """
            SELECT EXISTS (
                SELECT 1 FROM vms.user_role ur
                WHERE ur.user_id = CAST(:user AS uuid)
                  AND (ur.role IN ('ADMIN', 'OPS') OR (ur.role = 'PM' AND (ur.unit_id IS NULL OR ur.unit_id = bu.id)))
            ) AS manages
            FROM vms.business_unit bu
            WHERE bu.id = CAST(:unit AS uuid) AND bu.organization_id = CAST(:org AS uuid)
            """,
            {"unit": str(unit_id), "org": org_id, "user": user_id},
        )
