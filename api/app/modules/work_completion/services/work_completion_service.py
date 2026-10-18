"""
app/modules/work_completion/services/work_completion_service.py

Business logic service untuk pengelolaan Order Proyek Klien (Work Completion) VMS V3.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.security import CurrentUser
from app.modules.work_completion.crud.crud_work_completion import CRUDWorkCompletion


class WorkCompletionService:
    """Service logika bisnis Order Proyek Klien."""

    def __init__(self, crud: CRUDWorkCompletion) -> None:
        self.crud = crud

    async def list_orders(
        self,
        current_user: CurrentUser,
        *,
        division_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Membaca daftar order proyek dengan pembatasan hak akses multi-tenant/divisi."""
        # Jika PM, batasi hanya order miliknya atau divisinya
        target_pm: UUID | None = None
        if current_user.role == "PROJECT_MANAGER" and current_user.employee_id:
            target_pm = UUID(current_user.employee_id)

        items = await self.crud.list_completions(
            division_id=division_id,
            status=status,
            search=search,
            pm_id=target_pm,
            limit=limit,
            offset=offset,
        )
        total = await self.crud.count_completions(
            division_id=division_id,
            status=status,
            search=search,
            pm_id=target_pm,
        )
        return items, total

    async def get_order_detail(self, current_user: CurrentUser, completion_id: UUID) -> dict[str, Any]:
        """Mengambil rincian order proyek."""
        order = await self.crud.get_completion(completion_id)
        if not order:
            raise NotFoundError("Order Proyek Klien")
        return order

    async def create_order(self, current_user: CurrentUser, data: dict[str, Any]) -> dict[str, Any]:
        """Membuat order proyek baru."""
        if current_user.role not in ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat membuat Order Klien.")

        # Default PM ID ke pembuat jika PM
        if current_user.role == "PROJECT_MANAGER" and not data.get("pm_id"):
            data["pm_id"] = current_user.employee_id

        cid = await self.crud.create_completion(data)
        created = await self.crud.get_completion(cid)
        if not created:
            raise AppError("CREATE_FAILED", "Gagal mengambil data order yang baru dibuat.")
        return created

    async def update_order(
        self, current_user: CurrentUser, completion_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Memperbarui rincian order."""
        existing = await self.crud.get_completion(completion_id)
        if not existing:
            raise NotFoundError("Order Proyek Klien")

        if current_user.role == "PROJECT_MANAGER" and existing.get("pm_id") != current_user.employee_id:
            raise ForbiddenError("Anda hanya dapat mengedit Order Klien milik Anda.")

        await self.crud.update_completion(completion_id, data)
        updated = await self.crud.get_completion(completion_id)
        return updated or existing

    async def update_order_status(
        self,
        current_user: CurrentUser,
        completion_id: UUID,
        new_status: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Memperbarui status order (PM override)."""
        valid_statuses = ("PENDING", "CANCELLED", "ONGOING", "URGENT", "COMPLETED")
        if new_status not in valid_statuses:
            raise AppError("INVALID_STATUS", f"Status order harus salah satu dari: {', '.join(valid_statuses)}")

        existing = await self.crud.get_completion(completion_id)
        if not existing:
            raise NotFoundError("Order Proyek Klien")

        if current_user.role not in ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat mengubah status Order.")

        await self.crud.update_status(completion_id, new_status, notes)
        updated = await self.crud.get_completion(completion_id)
        return updated or existing

    async def sign_order(
        self,
        current_user: CurrentUser,
        completion_id: UUID,
        signature_data_url: str,
        summary_notes: str | None,
        obstacles: str | None,
        realization_photos: list[str],
    ) -> dict[str, Any]:
        """Membubuhkan tanda tangan digital pada Berita Acara Penyelesaian."""
        existing = await self.crud.get_completion(completion_id)
        if not existing:
            raise NotFoundError("Order Proyek Klien")

        if current_user.role not in ("TEAM_LEADER", "PROJECT_MANAGER", "OPERATIONAL_MANAGER", "SUPER_ADMIN"):
            raise ForbiddenError("Peran Anda tidak diizinkan menandatangani Berita Acara.")

        # Simpan tanda tangan PNG secara lokal
        sig_bytes = b""
        if "," in signature_data_url:
            sig_bytes = base64.b64decode(signature_data_url.split(",")[1])
        else:
            sig_bytes = base64.b64decode(signature_data_url)

        sig_hash = hashlib.sha256(sig_bytes).hexdigest()
        signer_id = current_user.employee_id or current_user.user_id
        sig_path = f"/uploads/inspections/sig_{completion_id}_{signer_id}.png"

        await self.crud.sign_completion(
            completion_id=completion_id,
            signer_id=signer_id,
            role=current_user.role,
            signature_path=sig_path,
            summary_notes=summary_notes,
            obstacles=obstacles,
            photos=realization_photos,
            signature_hash=sig_hash,
        )

        signed = await self.crud.get_completion(completion_id)
        return signed or existing
