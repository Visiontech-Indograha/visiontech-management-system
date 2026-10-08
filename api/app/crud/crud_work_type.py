"""
app/crud/crud_work_type.py
Jenis pekerjaan + template foto laporan (T9). Hanya SQL; aturan di services/work_type_service.py.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_SELECT = """
    SELECT wt.id, wt.name, wt.is_active,
           COALESCE((SELECT jsonb_agg(jsonb_build_object('id', p.id, 'sort_order', p.sort_order, 'label', p.label,
                                                         'hint', p.hint, 'required', p.required)
                                      ORDER BY p.sort_order)
                     FROM vms.work_type_photo p WHERE p.work_type_id = wt.id), '[]'::jsonb) AS photos
    FROM vms.work_type wt
    WHERE wt.organization_id = CAST(:org AS uuid)
"""


class CRUDWorkType(CRUDBase):
    """Akses data `work_type` dan `work_type_photo`."""

    async def list_types(self, org_id: UUID | str, include_inactive: bool) -> list[Any]:
        """Daftar jenis pekerjaan beserta slot fotonya, urut nama."""
        return list(await self.fetchall(
            _SELECT + " AND (wt.is_active OR CAST(:all AS boolean)) ORDER BY lower(wt.name)",
            {"org": str(org_id), "all": include_inactive}))

    async def get_type(self, org_id: UUID | str, type_id: UUID | str) -> Any:
        """Satu jenis pekerjaan (None bila bukan milik organisasi)."""
        return await self.fetchone(_SELECT + " AND wt.id = CAST(:id AS uuid)",
                                   {"org": str(org_id), "id": str(type_id)})

    async def name_taken(self, org_id: UUID | str, name: str, except_id: UUID | str | None) -> bool:
        """Nama sudah dipakai jenis lain (tanpa membedakan huruf besar/kecil)?"""
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.work_type WHERE organization_id = CAST(:org AS uuid) "
            "AND lower(name) = lower(:name) AND (CAST(:ex AS uuid) IS NULL OR id <> CAST(:ex AS uuid)))",
            {"org": str(org_id), "name": name, "ex": str(except_id) if except_id else None}))

    async def insert_type(self, org_id: UUID | str, name: str) -> str:
        """Jenis baru → id."""
        return str(await self.scalar(
            "INSERT INTO vms.work_type (organization_id, name) VALUES (CAST(:org AS uuid), :name) RETURNING id",
            {"org": str(org_id), "name": name}))

    async def update_type(self, type_id: UUID | str, name: str, is_active: bool | None = None) -> None:
        """Ubah nama (dan status aktif bila diberikan)."""
        await self.execute(
            "UPDATE vms.work_type SET name = :name, is_active = COALESCE(CAST(:act AS boolean), is_active) "
            "WHERE id = CAST(:id AS uuid)", {"id": str(type_id), "name": name, "act": is_active})

    async def replace_photos(self, org_id: UUID | str, type_id: UUID | str, photos: list[dict[str, Any]]) -> None:
        """Ganti seluruh daftar slot foto (urutan = urutan daftar)."""
        await self.execute("DELETE FROM vms.work_type_photo WHERE work_type_id = CAST(:id AS uuid)",
                           {"id": str(type_id)})
        for order, photo in enumerate(photos):
            await self.execute(
                "INSERT INTO vms.work_type_photo (organization_id, work_type_id, sort_order, label, hint, required) "
                "VALUES (CAST(:org AS uuid), CAST(:id AS uuid), :ord, :label, :hint, :req)",
                {"org": str(org_id), "id": str(type_id), "ord": order, "label": photo["label"],
                 "hint": photo.get("hint"), "req": bool(photo.get("required"))})

    async def type_is_usable(self, org_id: UUID | str, type_id: UUID | str) -> bool:
        """Jenis ada di organisasi ini dan aktif?"""
        return bool(await self.scalar(
            "SELECT EXISTS (SELECT 1 FROM vms.work_type WHERE id = CAST(:id AS uuid) "
            "AND organization_id = CAST(:org AS uuid) AND is_active)", {"id": str(type_id), "org": str(org_id)}))

    async def plan_type(self, plan_id: UUID | str) -> str | None:
        """Jenis pekerjaan yang terpasang pada rencana kerja (None = tanpa jenis)."""
        value = await self.scalar("SELECT CAST(work_type_id AS text) FROM vms.work_plan WHERE id = CAST(:id AS uuid)",
                                  {"id": str(plan_id)})
        return str(value) if value else None

    async def template_of_plan(self, plan_id: UUID | str) -> list[Any]:
        """Slot template rencana kerja (kosong bila tanpa jenis)."""
        return list(await self.fetchall(
            "SELECT p.id, p.sort_order, p.label, p.hint, p.required FROM vms.work_plan wp "
            "JOIN vms.work_type_photo p ON p.work_type_id = wp.work_type_id "
            "WHERE wp.id = CAST(:plan AS uuid) ORDER BY p.sort_order", {"plan": str(plan_id)}))

    async def missing_required_daily(self, plan_id: UUID | str, day_id: UUID | str) -> list[str]:
        """Label slot wajib yang belum punya foto pada laporan harian ketua."""
        rows = await self.fetchall(
            """
            SELECT p.label FROM vms.work_plan wp
            JOIN vms.work_type_photo p ON p.work_type_id = wp.work_type_id AND p.required
            WHERE wp.id = CAST(:plan AS uuid) AND NOT EXISTS (
                SELECT 1 FROM vms.daily_report r JOIN vms.report_evidence e ON e.daily_report_id = r.id
                WHERE r.work_plan_day_id = CAST(:day AS uuid) AND e.slot_label = p.label)
            ORDER BY p.sort_order
            """, {"plan": str(plan_id), "day": str(day_id)})
        return [str(r.label) for r in rows]

    async def missing_required_member(self, plan_id: UUID | str, report_id: UUID | str) -> list[str]:
        """Label slot wajib yang belum punya foto pada laporan anggota."""
        rows = await self.fetchall(
            """
            SELECT p.label FROM vms.work_plan wp
            JOIN vms.work_type_photo p ON p.work_type_id = wp.work_type_id AND p.required
            WHERE wp.id = CAST(:plan AS uuid) AND NOT EXISTS (
                SELECT 1 FROM vms.member_report_evidence e
                WHERE e.member_report_id = CAST(:rep AS uuid) AND e.slot_label = p.label)
            ORDER BY p.sort_order
            """, {"plan": str(plan_id), "rep": str(report_id)})
        return [str(r.label) for r in rows]
