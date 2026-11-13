"""Rute Arsip: daftar item terhapus dan pulihkan, per modul (peralatan, kendaraan, klien, divisi, jabatan, mess)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.deps import require_permission
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.archive.dependencies import get_archive_service
from app.modules.archive.schemas.archive_modules import ARCHIVE_MODULES
from app.modules.archive.schemas.archive_schema import ArchiveItemOut
from app.modules.archive.services.archive_service import ArchiveService

router = APIRouter(prefix="/archive", tags=["Archive"])


def _register(key: str, permission: Permission) -> None:
    guard = Depends(require_permission(permission))

    async def list_archived(
        response: Response,
        params: ListParams = Depends(),
        current_user: CurrentUser = guard,
        service: ArchiveService = Depends(get_archive_service),
    ) -> Any:
        rows = await service.list_deleted(key, current_user)
        return apply_list(rows, params, response, lambda r: (r["name"], r["code"]), prefix=True)

    async def restore_item(
        item_id: UUID,
        current_user: CurrentUser = guard,
        service: ArchiveService = Depends(get_archive_service),
    ) -> dict[str, Any]:
        return await service.restore(key, str(item_id), current_user)

    label = ARCHIVE_MODULES[key].label
    listing: Callable[..., Awaitable[Any]] = list_archived
    router.add_api_route(f"/{key}", listing, methods=["GET"], response_model=list[ArchiveItemOut],
                         summary=f"Arsip {label}", name=f"list_archived_{key.replace('-', '_')}")
    router.add_api_route(f"/{key}/{{item_id}}/restore", restore_item, methods=["POST"],
                         response_model=ArchiveItemOut, summary=f"Pulihkan {label}",
                         name=f"restore_{key.replace('-', '_')}")


for _key, _mod in ARCHIVE_MODULES.items():
    _register(_key, Permission(_mod.permission))
