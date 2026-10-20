"""
app/crud/crud_work_type.py
Jenis pekerjaan + template foto SOP Master Schema V2 (tabel work_type & image_requirement).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository

_SELECT = """
    SELECT wt.work_type_id AS id, wt.division_id, d.name AS division_name,
           wt.name, wt.description, (wt.delete_at IS NULL) AS is_active,
           COALESCE((SELECT jsonb_agg(jsonb_build_object(
                                         'id', p.image_requirement_id,
                                         'sort_order', p.sort_order,
                                         'label', p.name,
                                         'hint', p.path_image,
                                         'required', p.is_mandatory,
                                         'example_file_id', p.path_image)
                                      ORDER BY p.sort_order)
                     FROM image_requirement p
                     WHERE p.work_type_id = wt.work_type_id AND p.delete_at IS NULL), '[]'::jsonb) AS photos,
           COALESCE((SELECT jsonb_agg(jsonb_build_object(
                                         'default_material_id', m.default_material_id,
                                         'work_type_id', m.work_type_id,
                                         'material_code', m.material_code,
                                         'material_name', m.material_name,
                                         'default_qty', m.default_qty::float,
                                         'unit', m.unit,
                                         'category', m.category,
                                         'description', m.description,
                                         'sort_order', m.sort_order)
                                      ORDER BY m.sort_order, m.material_name)
                     FROM work_type_default_materials m
                     WHERE m.work_type_id = wt.work_type_id AND m.delete_at IS NULL), '[]'::jsonb) AS default_materials
    FROM work_type wt
    LEFT JOIN division d ON d.division_id = wt.division_id
    WHERE wt.delete_at IS NULL
"""


class WorkTypeRepository(BaseRepository):
    """Akses data Master Schema V2 work_type, image_requirement, dan default_materials."""
    """Akses data Master Schema V2 `work_type` dan `image_requirement`."""

    async def get_user_division(self, user_id: UUID | str) -> UUID | None:
        """Mendapatkan division_id karyawan dari user_id."""
        val = await self.scalar(
            """
            SELECT CAST(COALESCE(e.division_id, d_pm.division_id, d_om.division_id) AS uuid) AS division_id
            FROM users u
            LEFT JOIN employee e ON e.employee_id = u.employee_id AND e.delete_at IS NULL
            LEFT JOIN division d_pm ON (d_pm.pm_id = u.user_id OR d_pm.pm_id = u.employee_id) AND d_pm.delete_at IS NULL
            LEFT JOIN division d_om ON (d_om.om_id = u.user_id OR d_om.om_id = u.employee_id) AND d_om.delete_at IS NULL
            WHERE u.user_id = CAST(:uid AS uuid) AND u.delete_at IS NULL
            LIMIT 1
            """,
            {"uid": str(user_id)},
        )
        return UUID(str(val)) if val else None

    async def list_types(
        self, org_id: UUID | str, include_inactive: bool, division_id: UUID | str | None = None
    ) -> list[Any]:
        """Daftar jenis pekerjaan beserta slot fotonya, urut nama."""
        query = _SELECT
        params: dict[str, Any] = {"org": str(org_id), "all": include_inactive}
        if division_id is not None:
            query += " AND wt.division_id = CAST(:div_id AS uuid)"
            params["div_id"] = str(division_id)
        query += " ORDER BY lower(wt.name)"
        return list(await self.fetchall(query, params))

    async def get_type(self, org_id: UUID | str, type_id: UUID | str) -> Any:
        """Satu jenis pekerjaan."""
        return await self.fetchone(
            _SELECT + " AND wt.work_type_id = CAST(:id AS uuid)", {"org": str(org_id), "id": str(type_id)}
        )

    async def name_taken(
        self, org_id: UUID | str, division_id: UUID | str, name: str, except_id: UUID | str | None
    ) -> bool:
        """Nama sudah dipakai jenis lain dalam divisi yang sama (tanpa membedakan huruf besar/kecil)?"""
        return bool(
            await self.scalar(
                "SELECT EXISTS (SELECT 1 FROM work_type WHERE delete_at IS NULL "
                "AND division_id = CAST(:div_id AS uuid) "
                "AND lower(name) = lower(:name) AND (CAST(:ex AS uuid) IS NULL OR work_type_id <> CAST(:ex AS uuid)))",
                {"div_id": str(division_id), "name": name, "ex": str(except_id) if except_id else None},
            )
        )

    async def insert_type(
        self, org_id: UUID | str, division_id: UUID | str, name: str, description: str | None = None
    ) -> str:
        """Jenis baru → id."""
        return str(
            await self.scalar(
                "INSERT INTO work_type (division_id, name, description) "
                "VALUES (CAST(:div_id AS uuid), :name, :desc) RETURNING work_type_id",
                {"div_id": str(division_id), "name": name, "desc": description},
            )
        )

    async def update_type(
        self,
        type_id: UUID | str,
        name: str,
        division_id: UUID | str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        """Ubah nama dan divisi (atau soft delete bila nonaktif)."""
        if is_active is False:
            await self.execute(
                "UPDATE work_type SET delete_at = NOW() WHERE work_type_id = CAST(:id AS uuid)",
                {"id": str(type_id)},
            )
            return

        if division_id is not None:
            await self.execute(
                "UPDATE work_type SET name = :name, division_id = CAST(:div_id AS uuid), "
                "description = :desc, update_at = NOW() WHERE work_type_id = CAST(:id AS uuid)",
                {"id": str(type_id), "name": name, "div_id": str(division_id), "desc": description},
            )
        else:
            await self.execute(
                "UPDATE work_type SET name = :name, description = :desc, "
                "update_at = NOW() WHERE work_type_id = CAST(:id AS uuid)",
                {"id": str(type_id), "name": name, "desc": description},
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

    async def template_of_daily(self, daily_plan_id: UUID | str) -> list[Any]:
        """Slot template foto SOP (image_requirement) dari jenis pekerjaan item jadwal harian ini."""
        return list(
            await self.fetchall(
                """
            SELECT DISTINCT p.image_requirement_id AS id, p.sort_order, p.name AS label,
                   p.path_image AS hint, p.is_mandatory AS required, p.path_image AS example_file_id
            FROM image_requirement p
            JOIN work_plan_item wi ON wi.work_type_id = p.work_type_id
            WHERE wi.daily_plan_id = CAST(:day AS uuid) AND p.delete_at IS NULL AND wi.delete_at IS NULL
            ORDER BY p.sort_order
            """,
                {"day": str(daily_plan_id)},
            )
        )

    async def list_default_materials(self, work_type_id: UUID | str) -> list[Any]:
        """Daftar template material default untuk jenis pekerjaan tertentu."""
        sql = """
            SELECT
                default_material_id,
                work_type_id,
                material_code,
                material_name,
                default_qty::float AS default_qty,
                unit,
                category,
                description,
                sort_order
            FROM work_type_default_materials
            WHERE work_type_id = CAST(:wt_id AS uuid) AND delete_at IS NULL
            ORDER BY sort_order, material_name
        """
        return list(await self.fetchall(sql, {"wt_id": str(work_type_id)}))

    async def get_default_material(self, default_material_id: UUID | str) -> Any:
        """Satu template material default."""
        sql = """
            SELECT
                default_material_id,
                work_type_id,
                material_code,
                material_name,
                default_qty::float AS default_qty,
                unit,
                category,
                description,
                sort_order
            FROM work_type_default_materials
            WHERE default_material_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        return await self.fetchone(sql, {"id": str(default_material_id)})

    async def create_default_material(self, work_type_id: UUID | str, data: dict[str, Any]) -> str:
        """Membuat template material default baru untuk jenis pekerjaan."""
        sql = """
            INSERT INTO work_type_default_materials (
                work_type_id, material_code, material_name, default_qty,
                unit, category, description, sort_order
            )
            VALUES (
                CAST(:wt_id AS uuid), :code, :name, CAST(:qty AS numeric),
                :unit, :category, :description, CAST(:sort AS smallint)
            )
            RETURNING default_material_id
        """
        res = await self.scalar(
            sql,
            {
                "wt_id": str(work_type_id),
                "code": data.get("material_code"),
                "name": data["material_name"],
                "qty": data.get("default_qty", 1.0),
                "unit": data.get("unit", "Unit"),
                "category": data.get("category"),
                "description": data.get("description"),
                "sort": data.get("sort_order", 0),
            },
        )
        return str(res)

    async def update_default_material(self, default_material_id: UUID | str, data: dict[str, Any]) -> None:
        """Mengubah template material default."""
        updates: list[str] = ["update_at = NOW()"]
        params: dict[str, Any] = {"id": str(default_material_id)}

        if "material_code" in data:
            updates.append("material_code = :code")
            params["code"] = data["material_code"]
        if "material_name" in data and data["material_name"] is not None:
            updates.append("material_name = :name")
            params["name"] = data["material_name"]
        if "default_qty" in data and data["default_qty"] is not None:
            updates.append("default_qty = CAST(:qty AS numeric)")
            params["qty"] = data["default_qty"]
        if "unit" in data and data["unit"] is not None:
            updates.append("unit = :unit")
            params["unit"] = data["unit"]
        if "category" in data:
            updates.append("category = :category")
            params["category"] = data["category"]
        if "description" in data:
            updates.append("description = :description")
            params["description"] = data["description"]
        if "sort_order" in data and data["sort_order"] is not None:
            updates.append("sort_order = CAST(:sort AS smallint)")
            params["sort"] = data["sort_order"]

        set_clause = ", ".join(updates)
        sql = (
            f"UPDATE work_type_default_materials SET {set_clause} "
            "WHERE default_material_id = CAST(:id AS uuid) AND delete_at IS NULL"
        )
        await self.execute(sql, params)

    async def delete_default_material(self, default_material_id: UUID | str) -> None:
        """Soft delete template material default."""
        sql = """
            UPDATE work_type_default_materials
            SET delete_at = NOW(), update_at = NOW()
            WHERE default_material_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        await self.execute(sql, {"id": str(default_material_id)})


# Alias backward compatibility
CRUDWorkType = WorkTypeRepository
