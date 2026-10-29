"""
app/modules/work_completion/services/work_completion_service.py

Order Proyek Klien (Milestone 5, docs/35 §3): PM menerima order dari klien (mis. PHR) lalu menjadwalkannya
per hari/titik.
- Kelola (ubah, status, BoM): SUPER_ADMIN, PM order, atau PM/OM divisinya.
- Lihat: pengelola, ADMIN_HR_GA, atau anggota tim yang punya jadwal (disetujui) berisi item order ini.
- Tanda tangan BAST (docs/35 §8): ketua tim yang mengerjakan order lebih dulu (ringkasan + foto realisasi), lalu
  pengelola (PM/OM divisi). PNG tanda tangan disimpan di storage; setelah PM menandatangani, sidik SHA-256 atas isi
  dokumen disimpan di `signature_hash` dan order terkunci (`ORDER_LOCKED`). Verifikasi publik (QR) menghitung ulang.
Order tak terlihat → 404; terlihat tetapi tidak berwenang → 403.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any
from uuid import UUID

import filetype

from app.core import storage
from app.core.config import settings
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.modules.work_completion.repositories.work_completion_repository import (
    CRUDWorkCompletion,
)

FIELD_ROLES = ("TEAM_LEADER", "EMPLOYEE")
SIGNATURE_MAX_BYTES = 300_000
ORDER_LOCKED = "Serah terima sudah disetujui PM; pekerjaan klien ini tidak bisa diubah lagi."


def _iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value else None)


def completion_fingerprint(order: dict[str, Any], leader_png: bytes | None, pm_png: bytes | None) -> str:
    """SHA-256 atas isi berita acara yang disahkan: data order, ringkasan, foto, BoM, penanda tangan & PNG-nya."""
    bom = sorted(
        (str(b.get("material_code") or ""), str(b.get("material_name") or ""), float(b.get("estimated_qty") or 0),
         float(b.get("actual_qty") or 0), str(b.get("unit") or ""))
        for b in order.get("bom_items") or []
    )
    content = {
        "completion_id": str(order["completion_id"]),
        "order": [order.get(k) for k in ("order_number", "client_name", "project_title", "site_address",
                                         "total_target_unit", "unit_measure")],
        "summary_notes": order.get("summary_notes"),
        "obstacles": order.get("obstacles"),
        "photos": order.get("realization_photos_json") or [],
        "bom": bom,
        "leader": [str(order.get("leader_signer_id")), _iso(order.get("leader_signed_at")),
                   hashlib.sha256(leader_png or b"").hexdigest()],
        "pm": [str(order.get("pm_signer_id")), _iso(order.get("pm_signed_at")),
               hashlib.sha256(pm_png or b"").hexdigest()],
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def verify_url(order: dict[str, Any]) -> str | None:
    """Isi QR dokumen resmi: halaman verifikasi publik web."""
    h = order.get("signature_hash")
    return f"{settings.PUBLIC_VERIFY_URL.rstrip('/')}/work-completion/{order['completion_id']}?h={h}" if h else None


def _decode_png(data_url: str) -> bytes:
    raw = data_url.split(",", 1)[1] if data_url.startswith("data:") else data_url
    try:
        png = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError("Tanda tangan tidak terbaca. Ulangi tanda tangan.") from None
    if not png or len(png) > SIGNATURE_MAX_BYTES:
        raise ValidationError("Tanda tangan kosong atau terlalu besar (maks. 300 KB).")
    kind = filetype.guess(png)
    if kind is None or kind.mime != "image/png":
        raise ValidationError("Tanda tangan harus berupa gambar PNG.")
    return png


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
        if user.has_role("SUPER_ADMIN", "ADMIN_HR_GA"):
            return None, None
        if user.has_role(*FIELD_ROLES):
            return None, emp
        return emp, None

    async def _access(self, user: CurrentUser, completion_id: UUID, *, manage: bool) -> dict[str, Any]:
        order = await self.crud.get_completion(completion_id)
        standing = await self.crud.standing(completion_id, user.employee_id)
        if not order or standing is None:
            raise NotFoundError("Order Proyek Klien")
        admin = user.has_role("SUPER_ADMIN")
        manages = admin or bool(standing.manages)
        visible = manages or user.has_role("ADMIN_HR_GA") or bool(standing.on_team)
        if not visible:
            raise NotFoundError("Order Proyek Klien")
        if manage and not manages:
            raise ForbiddenError("Hanya PM order ini atau PM/OM divisinya yang dapat mengubahnya.")
        order["_on_team"] = bool(standing.on_team)
        return order

    async def _editable(self, user: CurrentUser, completion_id: UUID) -> dict[str, Any]:
        """Pengelola + belum disahkan PM (BAST resmi tidak boleh berubah setelah ditandatangani)."""
        order = await self._access(user, completion_id, manage=True)
        if order.get("pm_signed_at"):
            raise AppError("ORDER_LOCKED", ORDER_LOCKED, status=409)
        return order

    async def remove_photo(self, current_user: CurrentUser, completion_id: UUID, file_id: UUID) -> dict[str, Any]:
        """Hapus satu foto realisasi: ketua tim order ini atau pengelolanya, selama BAST belum disahkan PM."""
        order = await self._access(current_user, completion_id, manage=False)
        on_team = order.pop("_on_team", False)
        if order.get("pm_signed_at"):
            raise AppError("ORDER_LOCKED", ORDER_LOCKED, status=409)
        if not (current_user.has_role("TEAM_LEADER") and on_team):
            await self._access(current_user, completion_id, manage=True)
        if not await self.crud.remove_photo(completion_id, str(file_id)):
            raise NotFoundError("Foto hasil kerja")
        return await self.get_order_detail(current_user, completion_id)

    async def signature_png(self, current_user: CurrentUser, completion_id: UUID, role: str) -> bytes:
        """Gambar tanda tangan tersimpan (ketua/PM) untuk ditampilkan kembali; hanya bagi yang boleh melihat order."""
        order = await self.get_order_detail(current_user, completion_id)
        png = storage.get_image_bytes(order.get(f"{role}_signature_path") or "")
        if not png:
            raise NotFoundError("Tanda tangan")
        return png

    async def export_access(self, user: CurrentUser, completion_id: UUID) -> tuple[dict[str, Any], bool]:
        """Akses ekspor dokumen order: (order, penuh). Pengelola (PM order / PM-OM divisi) dan Super Admin = penuh.
        Ketua tim yang punya item di order = terbatas (False). Selain itu 403 (404 bila order tak terlihat)."""
        order = await self._access(user, completion_id, manage=False)
        on_team = order.pop("_on_team", False)
        standing = await self.crud.standing(completion_id, user.employee_id)
        if user.has_role("SUPER_ADMIN") or (standing is not None and standing.manages):
            return order, True
        if on_team and user.has_role("TEAM_LEADER"):
            return order, False
        raise ForbiddenError("Dokumen order ini hanya untuk PM/OM divisi. Ketua tim hanya dapat mengunduh "
                             "BAST dan slide progres untuk timnya.")

    async def get_order_detail(self, current_user: CurrentUser, completion_id: UUID) -> dict[str, Any]:
        """Mengambil rincian order proyek (yang terlihat oleh pengguna)."""
        order = await self._access(current_user, completion_id, manage=False)
        order.pop("_on_team", None)
        return order

    async def create_order(self, current_user: CurrentUser, data: dict[str, Any]) -> dict[str, Any]:
        """Membuat order proyek baru."""
        if not current_user.has_role("SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER"):
            raise ForbiddenError("Hanya PM, OM, atau Super Admin yang dapat membuat Order Klien.")
        if current_user.has_role("PROJECT_MANAGER"):
            if not current_user.employee_id:
                raise ForbiddenError("Akun PM ini belum tertaut ke data karyawan.")
            if data.get("pm_id") and str(data["pm_id"]) != str(current_user.employee_id):
                raise ForbiddenError("PM hanya dapat membuat order atas nama dirinya sendiri.")
            data["pm_id"] = current_user.employee_id
        if not data.get("division_id"):
            if data.get("project_id"):
                proj = await self.crud.project_snapshot(data["project_id"])
                if proj:
                    data["division_id"] = proj.division_id
            elif current_user.employee_id:
                pm_divs = await self.crud.get_pm_divisions(current_user.employee_id)
                if len(pm_divs) > 1:  # PM multi-divisi: order tidak boleh masuk ke divisi yang acak
                    raise AppError("DIVISION_REQUIRED", "Anda memimpin lebih dari satu divisi. Pilih divisi order ini.",
                                   status=422, details={"divisions": pm_divs})
                if pm_divs:
                    data["division_id"] = pm_divs[0]["division_id"]
        if not data.get("division_id"):
            raise ValidationError("Divisi order wajib ditentukan.")
        if not current_user.has_role("SUPER_ADMIN") and (
            not current_user.employee_id
            or not await self.crud.is_division_manager(data["division_id"], current_user.employee_id)
        ):
            raise ForbiddenError("Anda bukan PM/OM divisi order ini.")
        project = None
        if data.get("project_id"):
            project = await self.crud.project_snapshot(data["project_id"])
            if project is None or str(project.division_id) != str(data["division_id"]):
                raise ValidationError("Proyek tidak ditemukan di divisi order ini.")
            if project.status != "ONGOING":
                raise ValidationError("Proyek tidak sedang berjalan.")
            data["client_name"] = data.get("client_name") or project.client_name
            data["project_title"] = data.get("project_title") or project.project_title
            data["order_number"] = data.get("order_number") or project.spk_number[:50]
            data.setdefault("start_work_date", project.start_date)
            data.setdefault("end_work_date", project.end_date)
            if not current_user.has_role("PROJECT_MANAGER") and not data.get("pm_id"):
                data["pm_id"] = project.pm_id
        if not data.get("client_name") or not data.get("project_title"):
            raise ValidationError("Isi nama klien dan judul pekerjaan, atau pilih proyek.")
        pm_id = data.get("pm_id")
        if pm_id and await self.crud.employee_role(pm_id) != "PROJECT_MANAGER":
            raise ValidationError("PM order harus karyawan aktif dengan peran Project Manager.")
        if pm_id and not await self.crud.is_division_pm(data["division_id"], pm_id) and not (
            project is not None and str(project.pm_id) == str(pm_id)
        ):
            raise ValidationError("PM order harus ditugaskan pada divisi yang sama.")

        cid = await self.crud.create_completion(data)
        created = await self.crud.get_completion(cid)
        if not created:
            raise AppError("CREATE_FAILED", "Gagal mengambil data order yang baru dibuat.")
        return created

    async def delete_order(self, current_user: CurrentUser, completion_id: UUID) -> None:
        """Menghapus order proyek klien (soft delete)."""
        existing = await self._editable(current_user, completion_id)
        if existing.get("leader_signed_at") and not current_user.has_role("SUPER_ADMIN"):
            raise AppError("ORDER_LOCKED", "Order yang sudah ditandatangani ketua tim tidak dapat dihapus.", status=409)
        await self.crud.delete_completion(completion_id)

    async def update_order(
        self, current_user: CurrentUser, completion_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Memperbarui rincian order."""
        existing = await self._editable(current_user, completion_id)
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

        existing = await self._editable(current_user, completion_id)

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
        realization_photos: list[UUID],
    ) -> dict[str, Any]:
        """Tanda tangan BAST: ketua tim lebih dulu, lalu PM/OM divisi (mengesahkan & mengunci)."""
        existing = await self._access(current_user, completion_id, manage=False)
        on_team = existing.pop("_on_team", False)
        if existing.get("pm_signed_at"):
            raise AppError("ORDER_LOCKED", ORDER_LOCKED, status=409)
        as_leader = current_user.has_role("TEAM_LEADER")
        photo_ids: list[str] = []
        if as_leader:
            if not on_team:
                raise ForbiddenError("Hanya ketua tim yang mengerjakan order ini yang dapat menandatangani.")
            if not ((summary_notes or "").strip() or (existing.get("summary_notes") or "").strip()):
                raise ValidationError("Isi ringkasan pekerjaan sebelum menandatangani.")
            photo_ids = [str(p) for p in dict.fromkeys(realization_photos)]
            if photo_ids and await self.crud.existing_images(photo_ids) != len(photo_ids):
                raise ValidationError("Ada foto hasil kerja yang belum diunggah atau bukan gambar.")
        elif current_user.has_role(*FIELD_ROLES) or current_user.has_role("ADMIN_HR_GA"):
            raise ForbiddenError("Peran Anda tidak diizinkan menandatangani serah terima.")
        else:
            await self._access(current_user, completion_id, manage=True)
            if not existing.get("leader_signed_at"):
                raise AppError("LEADER_SIGNATURE_REQUIRED",
                               "Ketua tim harus menandatangani berita acara lebih dulu.", status=409)
        if not current_user.employee_id:
            raise ForbiddenError("Akun ini belum tertaut ke data karyawan.")

        png = _decode_png(signature_data_url)
        key = f"signatures/work-completion/{completion_id}/{'leader' if as_leader else 'pm'}.png"
        if not storage.upload_file(key, png, "image/png"):
            raise AppError("STORAGE_UNAVAILABLE", "Penyimpanan berkas sedang tidak tersedia. Coba lagi.", status=503)
        await self.crud.sign_completion(
            completion_id=completion_id,
            signer_id=current_user.employee_id,
            as_leader=as_leader,
            signature_key=key,
            summary_notes=(summary_notes or "").strip() or None,
            obstacles=(obstacles or "").strip() or None,
            photos=photo_ids or None,
        )
        signed = await self.crud.get_completion(completion_id)
        if not signed:
            raise NotFoundError("Order Proyek Klien")
        if as_leader:
            from app.modules.notifications.services.notification_service import NotificationService

            what = signed.get("project_title") or signed.get("order_number") or "order proyek"
            await NotificationService(self.crud.db).notify_division_managers(
                current_user.employee_id, "BAST_LEADER_SIGNED", "BAST menunggu tanda tangan PM",
                f"Ketua tim sudah menandatangani berita acara {what}.", target="work-completion",
            )
        if not as_leader:
            leader_png = storage.get_image_bytes(signed["leader_signature_path"] or "")
            signed["signature_hash"] = completion_fingerprint(signed, leader_png, png)
            await self.crud.set_signature_hash(completion_id, signed["signature_hash"])
        return signed

    async def verify(self, completion_id: UUID, signature_hash: str) -> dict[str, Any]:
        """Verifikasi publik (QR): sidik harus sama dengan yang tersimpan DAN dengan hitungan ulang isi saat ini.
        Sidik salah / belum disahkan → 404 (tidak membocorkan keberadaan order)."""
        order = await self.crud.get_completion(completion_id)
        if not order or not order.get("signature_hash") or order["signature_hash"] != signature_hash.lower():
            raise NotFoundError("Dokumen")
        leader_png = storage.get_image_bytes(order["leader_signature_path"] or "")
        pm_png = storage.get_image_bytes(order["pm_signature_path"] or "")
        return {
            "completion_id": order["completion_id"],
            "order_number": order.get("order_number"),
            "client_name": order.get("client_name"),
            "project_title": order.get("project_title"),
            "leader_signer_name": order.get("leader_signer_name"),
            "leader_signed_at": order.get("leader_signed_at"),
            "pm_signer_name": order.get("pm_signer_name"),
            "pm_signed_at": order.get("pm_signed_at"),
            "signature_hash": order["signature_hash"],
            "intact": completion_fingerprint(order, leader_png, pm_png) == order["signature_hash"],
        }

    async def list_bom_items(self, current_user: CurrentUser, completion_id: UUID) -> list[dict[str, Any]]:
        """Membaca daftar item BoM untuk satu order proyek klien."""
        await self.get_order_detail(current_user, completion_id)
        return await self.crud.list_bom_items(completion_id)

    async def add_bom_item(
        self, current_user: CurrentUser, completion_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Menambahkan item BoM baru."""
        await self._editable(current_user, completion_id)
        bom_id = await self.crud.add_bom_item(completion_id, data)
        item = await self.crud.get_bom_item(UUID(bom_id))
        if not item:
            raise AppError("CREATE_FAILED", "Gagal mengambil data material yang baru dibuat.")
        return item

    async def update_bom_item(
        self, current_user: CurrentUser, bom_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Memperbarui item BoM (misal realisasi actual_qty di lapangan)."""
        existing = await self.crud.get_bom_item(bom_id)
        if not existing:
            raise NotFoundError("Item Bill of Materials")
        await self._editable(current_user, UUID(str(existing["completion_id"])))
        await self.crud.update_bom_item(bom_id, data)
        updated = await self.crud.get_bom_item(bom_id)
        return updated or existing

    async def delete_bom_item(self, current_user: CurrentUser, bom_id: UUID) -> None:
        """Menghapus item BoM."""
        existing = await self.crud.get_bom_item(bom_id)
        if not existing:
            raise NotFoundError("Item Bill of Materials")
        await self._editable(current_user, UUID(str(existing["completion_id"])))
        await self.crud.delete_bom_item(bom_id)

    async def sync_bom_from_work_types(
        self, current_user: CurrentUser, completion_id: UUID, overwrite_existing: bool = False
    ) -> int:
        """Sinkronisasi otomatis template default materials dari jenis pekerjaan."""
        await self._editable(current_user, completion_id)
        return await self.crud.sync_bom_from_work_types(completion_id, overwrite_existing=overwrite_existing)

    async def decide_acc(
        self, current_user: CurrentUser, completion_id: UUID, decision: str, notes: str | None = None
    ) -> dict[str, Any]:
        """Menyimpan keputusan ACC klien (MENUNGGU_ACC, DITERIMA, DITOLAK_REWORK)."""
        await self._access(current_user, completion_id, manage=True)
        await self.crud.set_acc_decision(completion_id, decision, current_user.employee_id, notes)
        if decision == "DITOLAK_REWORK":
            await self.crud.reopen_items_for_rework(completion_id)
        return await self.get_order_detail(current_user, completion_id)

    async def create_revision(
        self,
        current_user: CurrentUser,
        completion_id: UUID,
        description: str,
        request_date: Any = None,
        create_survey: bool = False,
    ) -> dict[str, Any]:
        """Mencatat revisi/tambahan pekerjaan dari klien."""
        order = await self._access(current_user, completion_id, manage=True)
        survey_task_id = None
        if create_survey:
            from app.modules.work_plans.services.survey_service import SurveyService
            survey_svc = SurveyService(self.crud.db)
            div_id = order.get("division_id")
            title = f"Survei Revisi: {description[:50]}"
            survey_task_id = await survey_svc.create_revision_task({
                "division_id": str(div_id) if div_id else None,
                "title": title,
                "description": description,
                "client_id": str(order.get("client_id")) if order.get("client_id") else None,
                "completion_id": str(completion_id),
                "created_by_id": current_user.employee_id,
            })

        rev_id = await self.crud.create_revision(
            completion_id, description, request_date, current_user.employee_id, survey_task_id
        )
        return {"revision_id": rev_id, "survey_task_id": survey_task_id}

    async def list_revisions(self, current_user: CurrentUser, completion_id: UUID) -> list[dict[str, Any]]:
        """Membaca daftar revisi klien."""
        await self.get_order_detail(current_user, completion_id)
        return await self.crud.list_revisions(completion_id)
