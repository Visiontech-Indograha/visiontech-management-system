"""
app/crud/crud_work_type.py
Jenis pekerjaan + template foto SOP Master Schema V2 (tabel work_type & image_requirement).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .base import CRUDBase

_SELECT = """
    SELECT wt.work_type_id AS id, wt.name, (wt.delete_at IS NULL) AS is_active,
           COALESCE((SELECT jsonb_agg(jsonb_build_object(
                                         'id', p.image_requirement_id,
                                         'sort_order', p.sort_order,
                                         'label', p.name,
                                         'hint', p.path_image,
                                         'required', p.is_mandatory,
                                         'example_file_id', p.path_image)
                                      ORDER BY p.sort_order)
                     FROM image_requirement p
                     WHERE p.work_type_id = wt.work_type_id AND p.delete_at IS NULL), '[]'::jsonb) AS photos
    FROM work_type wt
    WHERE wt.delete_at IS NULL
"""


class CRUDWorkType(CRUDBase):
    """Akses data Master Schema V2 `work_type` dan `image_requirement`."""

    async def list_types(self, org_id: UUID | str, include_inactive: bool) -> list[Any]:
        """Daftar jenis pekerjaan beserta slot fotonya, urut nama."""
        return list(
            await self.fetchall(_SELECT + " ORDER BY lower(wt.name)", {"org": str(org_id), "all": include_inactive})
        )

    async def get_type(self, org_id: UUID | str, type_id: UUID | str) -> Any:
        """Satu jenis pekerjaan."""
        return await self.fetchone(
            _SELECT + " AND wt.work_type_id = CAST(:id AS uuid)", {"org": str(org_id), "id": str(type_id)}
        )

    async def name_taken(self, org_id: UUID | str, name: str, except_id: UUID | str | None) -> bool:
        """Nama sudah dipakai jenis lain (tanpa membedakan huruf besar/kecil)?"""
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM work_type WHERE delete_at IS NULL "
                "AND lower(name) = lower(:name) AND (CAST(:ex AS uuid) IS NULL OR work_type_id <> CAST(:ex AS uuid)))",
                {"org": str(org_id), "name": name, "ex": str(except_id) if except_id else None},
            )
        )

    async def insert_type(self, org_id: UUID | str, name: str) -> str:
        """Jenis baru → id."""
        return str(
            await self.scalar("INSERT INTO work_type (name) VALUES (:name) RETURNING work_type_id", {"name": name})
        )

    async def update_type(self, type_id: UUID | str, name: str, is_active: bool | None = None) -> None:
        """Ubah nama."""
        await self.execute(
            "UPDATE work_type SET name = :name, update_at = NOW() WHERE work_type_id = CAST(:id AS uuid)",
            {"id": str(type_id), "name": name},
        )

    async def replace_photos(self, org_id: UUID | str, type_id: UUID | str, photos: list[dict[str, Any]]) -> None:
        """Ganti seluruh daftar slot foto SOP (urutan = urutan daftar)."""
        await self.execute(
            """
            UPDATE image_requirement
            SET delete_at = NOW()
            WHERE work_type_id = CAST(:id AS uuid) AND delete_at IS NULL
            """,
            {"id": str(type_id)},
        )
        for order, photo in enumerate(photos, start=1):
            await self.execute(
                """
                INSERT INTO image_requirement (work_type_id, name, path_image, is_mandatory, sort_order)
                VALUES (CAST(:id AS uuid), :name, :path, :req, :ord)
                """,
                {
                    "id": str(type_id),
                    "name": photo["label"],
                    "path": photo.get("hint") or photo.get("example_file_id") or "sop/placeholder.jpg",
                    "req": bool(photo.get("required", True)),
                    "ord": order,
                },
            )

    async def type_is_usable(self, org_id: UUID | str, type_id: UUID | str) -> bool:
        """Jenis ada dan aktif?"""
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM work_type WHERE work_type_id = CAST(:id AS uuid) AND delete_at IS NULL)",
                {"id": str(type_id)},
            )
        )

    async def plan_type(self, plan_id: UUID | str) -> str | None:
        """Jenis pekerjaan yang terpasang pada item rencana kerja."""
        value = await self.scalar(
            """
            SELECT CAST(wi.work_type_id AS text)
            FROM work_plan_item wi
            JOIN work_plan_daily wd ON wd.daily_plan_id = wi.daily_plan_id
            WHERE wd.weekly_plan_id = CAST(:id AS uuid) AND wi.delete_at IS NULL
            LIMIT 1
            """,
            {"id": str(plan_id)},
        )
        return str(value) if value else None

    async def template_of_plan(self, plan_id: UUID | str, day_id: UUID | str | None = None) -> list[Any]:
        """Slot template foto SOP dari jenis pekerjaan pada rencana kerja."""
        return list(
            await self.fetchall(
                """
            SELECT p.image_requirement_id AS id, p.sort_order, p.name AS label,
                   p.path_image AS hint, p.is_mandatory AS required, p.path_image AS example_file_id
            FROM image_requirement p
            JOIN work_plan_item wi ON wi.work_type_id = p.work_type_id
            JOIN work_plan_daily wd ON wd.daily_plan_id = wi.daily_plan_id
            WHERE wd.weekly_plan_id = CAST(:plan AS uuid)
              AND (CAST(:day AS uuid) IS NULL OR wd.daily_plan_id = CAST(:day AS uuid))
              AND p.delete_at IS NULL AND wi.delete_at IS NULL
            ORDER BY p.sort_order
            """,
                {"plan": str(plan_id), "day": str(day_id) if day_id else None},
            )
        )

    async def type_in_plan(self, plan_id: UUID | str, type_id: UUID | str) -> bool:
        """Jenis ini sudah terpasang pada rencana kerja?"""
        return bool(
            await self.scalar(
                """
            SELECT EXISTS (
                SELECT 1 FROM work_plan_item wi
                JOIN work_plan_daily wd ON wd.daily_plan_id = wi.daily_plan_id
                WHERE wd.weekly_plan_id = CAST(:plan AS uuid) AND wi.work_type_id = CAST(:wt AS uuid)
                  AND wi.delete_at IS NULL AND wd.delete_at IS NULL
            )
            """,
                {"plan": str(plan_id), "wt": str(type_id)},
            )
        )

    async def missing_required_daily(self, plan_id: UUID | str, day_id: UUID | str) -> list[str]:
        """Label slot wajib yang belum punya foto."""
        rows = await self.fetchall(
            """
            SELECT p.name AS label
            FROM image_requirement p
            JOIN work_plan_item wi ON wi.work_type_id = p.work_type_id
            WHERE wi.daily_plan_id = CAST(:day AS uuid)
              AND p.is_mandatory = TRUE
              AND p.delete_at IS NULL
              AND (wi.photo_urls IS NULL OR jsonb_array_length(wi.photo_urls) = 0)
            ORDER BY p.sort_order
            """,
            {"day": str(day_id)},
        )
        return [str(r.label) for r in rows]

    async def missing_required_member(self, plan_id: UUID | str, report_id: UUID | str) -> list[str]:
        """Label slot wajib yang belum punya foto pada laporan."""
        return await self.missing_required_daily(plan_id, report_id)
