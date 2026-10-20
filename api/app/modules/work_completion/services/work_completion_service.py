"""
app/modules/work_completion/services/work_completion_service.py

Order Proyek Klien (Milestone 5, docs/35 §3): PM menerima order dari klien (mis. PHR) lalu menjadwalkannya
per hari/titik.
- Kelola (ubah, status, BoM): SUPER_ADMIN, PM order, atau PM/OM divisinya.
- Lihat: pengelola, ADMIN_HR_GA, atau anggota tim yang punya jadwal (disetujui) berisi item order ini.
- Tanda tangan BAST: ketua tim yang mengerjakan order, atau pengelolanya.
Order tak terlihat → 404; terlihat tetapi tidak berwenang → 403.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any
from uuid import UUID

from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.work_completion.repositories.work_completion_repository import (
    CRUDWorkCompletion,
)
from app.shared.documents.document_export_service import DocumentExportService

FIELD_ROLES = ("TEAM_LEADER", "EMPLOYEE")


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
        target_pm, field = self._list_scope(current_user)

        items = await self.crud.list_completions(
            division_id=division_id,
            status=status,
            search=search,
            pm_id=target_pm,
            field_employee=field,
            limit=limit,
            offset=offset,
        )
        total = await self.crud.count_completions(
            division_id=division_id,
            status=status,
            search=search,
            pm_id=target_pm,
            field_employee=field,
        )
        return items, total

    @staticmethod
    def _list_scope(user: CurrentUser) -> tuple[UUID | None, UUID | None]:
        """(pengelola, lapangan) untuk penyaring daftar; (None, None) = semua (SUPER_ADMIN, ADMIN_HR_GA)."""
        emp = UUID(user.employee_id) if user.employee_id else UUID(int=0)
        if user.role in ("SUPER_ADMIN", "ADMIN_HR_GA"):
            return None, None
        if user.role in FIELD_ROLES:
            return None, emp
        return emp, None

    async def _access(self, user: CurrentUser, completion_id: UUID, *, manage: bool) -> dict[str, Any]:
        order = await self.crud.get_completion(completion_id)
        standing = await self.crud.standing(completion_id, user.employee_id)
        if not order or standing is None:
            raise NotFoundError("Order Proyek Klien")
        admin = user.role == "SUPER_ADMIN"
        manages = admin or bool(standing.manages)
        visible = manages or user.role == "ADMIN_HR_GA" or bool(standing.on_team)
        if not visible:
            raise NotFoundError("Order Proyek Klien")
        if manage and not manages:
            raise ForbiddenError("Hanya PM order ini atau PM/OM divisinya yang dapat mengubahnya.")
        order["_on_team"] = bool(standing.on_team)
        return order

    async def get_order_detail(self, current_user: CurrentUser, completion_id: UUID) -> dict[str, Any]:
        """Mengambil rincian order proyek (yang terlihat oleh pengguna)."""
        order = await self._access(current_user, completion_id, manage=False)
        order.pop("_on_team", None)
        return order

    async def create_order(self, current_user: CurrentUser, data: dict[str, Any]) -> dict[str, Any]:
        """Membuat order proyek baru."""
        if current_user.role not in ("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat membuat Order Klien.")
        if current_user.role == "PROJECT_MANAGER" and not data.get("pm_id"):
            data["pm_id"] = current_user.employee_id
        pm_id = data.get("pm_id")
        if pm_id and await self.crud.employee_role(pm_id) != "PROJECT_MANAGER":
            raise ValidationError("PM order harus karyawan aktif dengan peran Project Manager.")

        cid = await self.crud.create_completion(data)
        created = await self.crud.get_completion(cid)
        if not created:
            raise AppError("CREATE_FAILED", "Gagal mengambil data order yang baru dibuat.")
        return created

    async def update_order(
        self, current_user: CurrentUser, completion_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Memperbarui rincian order."""
        existing = await self._access(current_user, completion_id, manage=True)
        if data.get("pm_id") and await self.crud.employee_role(data["pm_id"]) != "PROJECT_MANAGER":
            raise ValidationError("PM order harus karyawan aktif dengan peran Project Manager.")

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

        existing = await self._access(current_user, completion_id, manage=True)

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
        existing = await self._access(current_user, completion_id, manage=False)
        if current_user.role == "TEAM_LEADER":
            if not existing.pop("_on_team", False):
                raise ForbiddenError("Hanya ketua tim yang mengerjakan order ini yang dapat menandatangani.")
        elif current_user.role in FIELD_ROLES or current_user.role == "ADMIN_HR_GA":
            raise ForbiddenError("Peran Anda tidak diizinkan menandatangani Berita Acara.")
        else:
            await self._access(current_user, completion_id, manage=True)

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

    async def list_bom_items(self, current_user: CurrentUser, completion_id: UUID) -> list[dict[str, Any]]:
        """Membaca daftar item BoM untuk satu order proyek klien."""
        await self.get_order_detail(current_user, completion_id)
        return await self.crud.list_bom_items(completion_id)

    async def add_bom_item(
        self, current_user: CurrentUser, completion_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Menambahkan item BoM baru."""
        await self._access(current_user, completion_id, manage=True)
        bom_id = await self.crud.add_bom_item(completion_id, data)
        item = await self.crud.get_bom_item(UUID(bom_id))
        if not item:
            raise AppError("CREATE_FAILED", "Gagal mengambil data item BoM yang baru dibuat.")
        return item

    async def update_bom_item(
        self, current_user: CurrentUser, bom_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Memperbarui item BoM (misal realisasi actual_qty di lapangan)."""
        existing = await self.crud.get_bom_item(bom_id)
        if not existing:
            raise NotFoundError("Item Bill of Materials")
        await self._access(current_user, UUID(str(existing["completion_id"])), manage=True)
        await self.crud.update_bom_item(bom_id, data)
        updated = await self.crud.get_bom_item(bom_id)
        return updated or existing

    async def delete_bom_item(self, current_user: CurrentUser, bom_id: UUID) -> None:
        """Menghapus item BoM."""
        existing = await self.crud.get_bom_item(bom_id)
        if not existing:
            raise NotFoundError("Item Bill of Materials")
        await self._access(current_user, UUID(str(existing["completion_id"])), manage=True)
        await self.crud.delete_bom_item(bom_id)

    async def sync_bom_from_work_types(
        self, current_user: CurrentUser, completion_id: UUID, overwrite_existing: bool = False
    ) -> int:
        """Sinkronisasi otomatis template default materials dari jenis pekerjaan."""
        await self._access(current_user, completion_id, manage=True)
        return await self.crud.sync_bom_from_work_types(completion_id, overwrite_existing=overwrite_existing)

    async def export_completion_docx(self, current_user: CurrentUser, completion_id: UUID) -> tuple[bytes, str]:
        """Ekspor Berita Acara & BoM ke dalam format Microsoft Word (.docx)."""
        detail = await self.get_order_detail(current_user, completion_id)
        docx_bytes = DocumentExportService.export_completion_docx(detail)
        client_clean = "".join(c for c in (detail.get("client_name") or "Order") if c.isalnum() or c in ("-", "_"))
        filename = f"BAST_BoM_{client_clean}_{str(completion_id)[:8]}.docx"
        return docx_bytes, filename
