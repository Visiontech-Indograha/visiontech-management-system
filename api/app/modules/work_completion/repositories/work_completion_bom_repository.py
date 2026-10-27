"""
app/modules/work_completion/repositories/work_completion_bom_repository.py
Akses data Bill of Materials (BoM) untuk order proyek klien.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.repository import BaseRepository
from app.modules.work_completion.repositories.work_completion_core_repository import _row_to_dict


class WorkCompletionBomRepository(BaseRepository):
    """Query dan manipulasi data BoM order klien."""

    async def list_bom_items(self, completion_id: UUID | str) -> list[dict[str, Any]]:
        """Daftar item BoM riil untuk satu order proyek klien."""
        sql = """
            SELECT
                bom_id,
                completion_id,
                work_plan_item_id,
                material_code,
                material_name,
                estimated_qty::float AS estimated_qty,
                actual_qty::float AS actual_qty,
                unit,
                category,
                notes,
                sort_order,
                create_at,
                update_at
            FROM work_completion_bom
            WHERE completion_id = CAST(:cid AS uuid) AND delete_at IS NULL
              -- survei: KEBUTUHAN (alat/izin) & KABEL (ukuran) bukan material BoM/BoQ
              AND COALESCE(category, 'MATERIAL') NOT IN ('KEBUTUHAN', 'KABEL')
            ORDER BY sort_order, material_name
        """
        rows = await self.fetchall(sql, {"cid": str(completion_id)})
        return [_row_to_dict(r) for r in rows]

    async def get_bom_item(self, bom_id: UUID | str) -> dict[str, Any] | None:
        """Satu item BoM."""
        sql = """
            SELECT
                bom_id,
                completion_id,
                work_plan_item_id,
                material_code,
                material_name,
                estimated_qty::float AS estimated_qty,
                actual_qty::float AS actual_qty,
                unit,
                category,
                notes,
                sort_order,
                create_at,
                update_at
            FROM work_completion_bom
            WHERE bom_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        row = await self.fetchone(sql, {"id": str(bom_id)})
        return _row_to_dict(row) if row else None

    async def add_bom_item(self, completion_id: UUID | str, data: dict[str, Any]) -> str:
        """Menambahkan item BoM baru ke order proyek klien."""
        sql = """
            INSERT INTO work_completion_bom (
                completion_id, work_plan_item_id, material_code, material_name,
                estimated_qty, actual_qty, unit, category, notes, sort_order
            )
            VALUES (
                CAST(:cid AS uuid),
                CAST(:item_id AS uuid),
                :code,
                :name,
                CAST(:est_qty AS numeric),
                CAST(:act_qty AS numeric),
                :unit,
                :category,
                :notes,
                CAST(:sort AS smallint)
            )
            RETURNING bom_id
        """
        res = await self.scalar(
            sql,
            {
                "cid": str(completion_id),
                "item_id": str(data["work_plan_item_id"]) if data.get("work_plan_item_id") else None,
                "code": data.get("material_code"),
                "name": data["material_name"],
                "est_qty": data.get("estimated_qty", 0.0),
                "act_qty": data.get("actual_qty", 0.0),
                "unit": data.get("unit", "Unit"),
                "category": data.get("category"),
                "notes": data.get("notes"),
                "sort": data.get("sort_order", 0),
            },
        )
        return str(res)

    async def update_bom_item(self, bom_id: UUID | str, data: dict[str, Any]) -> None:
        """Memperbarui item BoM (misal: pengisian pemakaian aktual di lapangan)."""
        updates: list[str] = ["update_at = NOW()"]
        params: dict[str, Any] = {"id": str(bom_id)}

        if "work_plan_item_id" in data:
            updates.append("work_plan_item_id = CAST(:item_id AS uuid)")
            params["item_id"] = str(data["work_plan_item_id"]) if data["work_plan_item_id"] else None
        if "material_code" in data:
            updates.append("material_code = :code")
            params["code"] = data["material_code"]
        if "material_name" in data and data["material_name"] is not None:
            updates.append("material_name = :name")
            params["name"] = data["material_name"]
        if "estimated_qty" in data and data["estimated_qty"] is not None:
            updates.append("estimated_qty = CAST(:est_qty AS numeric)")
            params["est_qty"] = data["estimated_qty"]
        if "actual_qty" in data and data["actual_qty"] is not None:
            updates.append("actual_qty = CAST(:act_qty AS numeric)")
            params["act_qty"] = data["actual_qty"]
        if "unit" in data and data["unit"] is not None:
            updates.append("unit = :unit")
            params["unit"] = data["unit"]
        if "category" in data:
            updates.append("category = :category")
            params["category"] = data["category"]
        if "notes" in data:
            updates.append("notes = :notes")
            params["notes"] = data["notes"]
        if "sort_order" in data and data["sort_order"] is not None:
            updates.append("sort_order = CAST(:sort AS smallint)")
            params["sort"] = data["sort_order"]

        set_clause = ", ".join(updates)
        sql = f"UPDATE work_completion_bom SET {set_clause} WHERE bom_id = CAST(:id AS uuid) AND delete_at IS NULL"
        await self.execute(sql, params)

    async def delete_bom_item(self, bom_id: UUID | str) -> None:
        """Soft delete item BoM."""
        sql = """
            UPDATE work_completion_bom
            SET delete_at = NOW(), update_at = NOW()
            WHERE bom_id = CAST(:id AS uuid) AND delete_at IS NULL
        """
        await self.execute(sql, {"id": str(bom_id)})

    async def sync_bom_from_work_types(self, completion_id: UUID | str, overwrite_existing: bool = False) -> int:
        """
        Menyalin template material default dari jenis pekerjaan (work_type) seluruh item tugas
        yang terhubung ke order klien ini ke dalam work_completion_bom.
        """
        if overwrite_existing:
            await self.execute(
                """
                UPDATE work_completion_bom
                SET delete_at = NOW(), update_at = NOW()
                WHERE completion_id = CAST(:cid AS uuid) AND delete_at IS NULL
                """,
                {"cid": str(completion_id)},
            )

        sql_fetch_defaults = """
            SELECT DISTINCT ON (COALESCE(dm.material_code, dm.material_name))
                dm.material_code,
                dm.material_name,
                dm.default_qty,
                dm.unit,
                dm.category,
                dm.description,
                dm.sort_order,
                wpi.item_id AS linked_item_id
            FROM work_plan_item wpi
            JOIN work_type_default_materials dm ON dm.work_type_id = wpi.work_type_id
            WHERE wpi.completion_id = CAST(:cid AS uuid)
              AND wpi.delete_at IS NULL
              AND dm.delete_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM work_completion_bom b
                  WHERE b.completion_id = CAST(:cid AS uuid)
                    AND b.delete_at IS NULL
                    AND (
                        (b.material_code IS NOT NULL AND b.material_code = dm.material_code)
                        OR lower(b.material_name) = lower(dm.material_name)
                    )
              )
            ORDER BY COALESCE(dm.material_code, dm.material_name), dm.sort_order
        """
        rows = await self.fetchall(sql_fetch_defaults, {"cid": str(completion_id)})
        count = 0
        for r in rows:
            await self.execute(
                """
                INSERT INTO work_completion_bom (
                    completion_id, work_plan_item_id, material_code, material_name,
                    estimated_qty, actual_qty, unit, category, notes, sort_order
                )
                VALUES (
                    CAST(:cid AS uuid),
                    CAST(:item_id AS uuid),
                    :code,
                    :name,
                    CAST(:qty AS numeric),
                    0.0,
                    :unit,
                    :category,
                    :notes,
                    CAST(:sort AS smallint)
                )
                """,
                {
                    "cid": str(completion_id),
                    "item_id": str(r.linked_item_id) if r.linked_item_id else None,
                    "code": r.material_code,
                    "name": r.material_name,
                    "qty": float(r.default_qty or 1.0),
                    "unit": r.unit or "Unit",
                    "category": r.category,
                    "notes": r.description,
                    "sort": int(r.sort_order or 0),
                },
            )
            count += 1
        return count
