"""
app/modules/image_requirements/repositories/image_requirement_repository.py
Repository akses basis data untuk tabel image_requirement.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from app.crud.base import CRUDBase
from app.modules.image_requirements.schemas.image_requirement_schema import (
    ImageRequirementCreate,
    ImageRequirementUpdate,
)


class ImageRequirementRepository(CRUDBase):
    """Akses query untuk data persyaratan foto jenis pekerjaan."""

    async def list_by_work_type(self, work_type_id: UUID) -> Sequence[Any]:
        sql = """
            SELECT
                r.image_requirement_id,
                r.work_type_id,
                r.name,
                r.description,
                r.path_image,
                r.is_mandatory,
                r.sort_order,
                r.create_at,
                w.name AS work_type_name
            FROM image_requirement r
            JOIN work_type w ON w.work_type_id = r.work_type_id
            WHERE r.work_type_id = :wt_id AND r.delete_at IS NULL
            ORDER BY r.sort_order ASC, r.create_at ASC
        """
        return await self.fetchall(sql, {"wt_id": work_type_id})

    async def get_by_id(self, requirement_id: UUID) -> Any | None:
        sql = """
            SELECT
                r.image_requirement_id,
                r.work_type_id,
                r.name,
                r.description,
                r.path_image,
                r.is_mandatory,
                r.sort_order,
                r.create_at,
                w.name AS work_type_name
            FROM image_requirement r
            JOIN work_type w ON w.work_type_id = r.work_type_id
            WHERE r.image_requirement_id = :id AND r.delete_at IS NULL
        """
        return await self.fetchone(sql, {"id": requirement_id})

    async def create_requirement(self, data: ImageRequirementCreate) -> Any:
        req_id = uuid.uuid4()
        sql = """
            INSERT INTO image_requirement (
                image_requirement_id, work_type_id, name, description, path_image,
                is_mandatory, sort_order, create_at, update_at
            ) VALUES (
                :id, :wt_id, :name, :description, :path,
                :mandatory, :sort, NOW(), NOW()
            )
            RETURNING image_requirement_id
        """
        await self.execute(sql, {
            "id": req_id,
            "wt_id": data.work_type_id,
            "name": data.name,
            "description": data.description,
            "path": data.path_image,
            "mandatory": data.is_mandatory,
            "sort": data.sort_order,
        })
        return await self.get_by_id(req_id)

    async def update_requirement(self, requirement_id: UUID, data: ImageRequirementUpdate) -> Any | None:
        updates: list[str] = ["update_at = NOW()"]
        params: dict[str, Any] = {"id": requirement_id}
        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.path_image is not None:
            updates.append("path_image = :path")
            params["path"] = data.path_image
        if data.is_mandatory is not None:
            updates.append("is_mandatory = :mandatory")
            params["mandatory"] = data.is_mandatory
        if data.sort_order is not None:
            updates.append("sort_order = :sort")
            params["sort"] = data.sort_order

        set_clause = ", ".join(updates)
        sql = f"UPDATE image_requirement SET {set_clause} WHERE image_requirement_id = :id AND delete_at IS NULL"
        await self.execute(sql, params)
        return await self.get_by_id(requirement_id)

    async def delete_requirement(self, requirement_id: UUID) -> bool:
        sql = "UPDATE image_requirement SET delete_at = NOW() WHERE image_requirement_id = :id AND delete_at IS NULL"
        await self.execute(sql, {"id": requirement_id})
        return True
