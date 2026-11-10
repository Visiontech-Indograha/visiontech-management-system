"""
app/modules/employees/services/employee_service.py
Karyawan V2 (Milestone 10).

- Baca: semua yang login (`view:users`, direktori). Kelola: HR (`manage:users`).
- No. karyawan unik; kantor wajib ada; divisi & jabatan aktif; jabatan per divisi harus sama dengan divisi karyawan;
  akhir PKWT ≥ tanggal bergabung; foto = berkas gambar yang sudah diunggah.
- Masa kerja diakhiri lewat modul offboarding (clearance aset), bukan di sini. Arsip hanya untuk yang sudah offboarded.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from app.core.audit_log import record_audit
from app.core.errors import AppError, ForbiddenError, NotFoundError, ValidationError
from app.core.file_cleanup import employee_keys, release_keys
from app.core.hard_delete import write_delete_audit
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.employees.repositories.employee_repository import EmployeeRepository
from app.modules.employees.schemas.employee_schema import AddressIn, EmployeeCreate, EmployeeUpdate
from app.shared.access.office_scope import ensure_office_in_scope
from app.shared.access.scope_rules import employee_params_scoped, sees_sensitive_employee_fields

logger = logging.getLogger(__name__)

ARCHIVED = "Karyawan diarsipkan. Data historis tetap tersimpan."
RESTORED = "Arsip dibatalkan. Karyawan tetap berstatus selesai bekerja."

# Kolom sensitif: hanya HR/OM/SA, PM yang menjangkau karyawan itu, dan pemiliknya.
_AUDIT_FIELDS = ("employee_no", "office_id", "division_id", "position_id", "join_date")
# Hanya nama bidang yang dicatat bila berubah (tanpa nilai): nama lengkap, telepon, akhir PKWT, foto.
_AUDIT_MASKED = ("full_name", "phone_number", "pkwt_end_date", "photo_file_id")
_SENSITIVE_FIELDS = ("phone_number", "email", "city", "pkwt_end_date", "system_role", "account_active")


def _shape(row: Mapping[str, Any]) -> dict[str, Any]:
    """Baris karyawan siap dipakai skema: `sensitive_ok` dibuang, kolom sensitif dikosongkan bila tak berhak."""
    data = dict(row)
    sensitive_ok = bool(data.pop("sensitive_ok", True))
    if not sensitive_ok:
        for key in _SENSITIVE_FIELDS:
            data[key] = None
    return data


class EmployeeService:
    def __init__(self, repo: EmployeeRepository) -> None:
        self.repo = repo

    async def list(self, *, page: int, size: int, status: str | None, division_id: UUID | None,
                   office_id: UUID | None, position_id: UUID | None, q: str | None,
                   user: CurrentUser | None = None) -> tuple[list[dict[str, Any]], int]:
        """Direktori sesuai cakupan pengguna: SA/OM/HR/Finance/HSE/aset semua; PM jangkauannya; lainnya
        dirinya, sesama divisi, dan sesama tim. Kolom sensitif dikosongkan bila tidak berhak."""
        if user is not None and not sees_sensitive_employee_fields(user) and status not in (None, "all", "active"):
            raise ForbiddenError("Filter status kepegawaian hanya untuk HR/OM.")
        scope = await employee_params_scoped(self.repo.db, user) if user is not None else None
        filters = {"status": status, "division_id": division_id, "office_id": office_id,
                   "position_id": position_id, "q": (q or "").strip() or None}
        rows = await self.repo.page(size, (page - 1) * size, scope=scope, **filters)
        total = await self.repo.count(scope=scope, **filters)
        return [_shape(r._mapping) for r in rows], total

    async def _audit(
        self, user: CurrentUser | None, action: str, employee_id: Any, before: Any = None, after: Any = None,
        *, skip_if_empty: bool = False,
    ) -> None:
        """Catat perubahan data karyawan; pemanggil internal tanpa pengguna tidak dicatat."""
        if user is None:
            return
        await record_audit(
            self.repo.db, user, action=action, entity_type="employee", entity_id=employee_id,
            before=before, after=after, fields=_AUDIT_FIELDS, masked=_AUDIT_MASKED, skip_if_empty=skip_if_empty,
        )

    async def get(self, employee_id: UUID, user: CurrentUser | None = None) -> Any:
        scope = await employee_params_scoped(self.repo.db, user) if user is not None else None
        row = await self.repo.get(employee_id, scope)
        if row is None:
            raise NotFoundError("Karyawan")
        return row

    async def detail(self, employee_id: UUID, user: CurrentUser | None = None) -> dict[str, Any]:
        row = await self.get(employee_id, user)
        data = dict(row._mapping)
        sensitive_ok = bool(data.get("sensitive_ok", True))
        addresses = [dict(a._mapping) for a in await self.repo.addresses(employee_id)] if sensitive_ok else []
        return {**_shape(row._mapping), "addresses": addresses}

    async def _validate(self, fields: dict[str, Any], current: Any = None) -> dict[str, Any]:
        """Periksa referensi & ubah photo_file_id → photo_path; kembalikan kolom siap simpan."""
        out = dict(fields)
        if out.get("employee_no"):
            out["employee_no"] = out["employee_no"].strip()
            if await self.repo.employee_no_taken(out["employee_no"], exclude=current.employee_id if current else None):
                raise AppError("EMPLOYEE_NO_TAKEN", "No. karyawan sudah dipakai.", status=409)
        if out.get("full_name"):
            out["full_name"] = out["full_name"].strip()
        division = out.get("division_id", current.division_id if current else None)
        position = out.get("position_id", current.position_id if current else None)
        refs = await self.repo.refs(out.get("office_id"), out.get("division_id"), out.get("position_id"))
        if not refs.office_ok:
            raise ValidationError("Kantor tidak ditemukan.")
        if not refs.division_ok:
            raise ValidationError("Divisi tidak ditemukan atau nonaktif.")
        if not refs.position_ok:
            raise ValidationError("Jabatan tidak ditemukan atau nonaktif.")
        if position and "position_id" in out:
            pos_div = refs.position_division
        elif position and current is not None:
            pos_div = (await self.repo.refs(None, None, position)).position_division
        else:
            pos_div = None
        if pos_div is not None and str(pos_div) != str(division):
            raise ValidationError("Jabatan ini milik divisi lain.")
        join = out.get("join_date", current.join_date if current else None)
        end = out.get("pkwt_end_date", current.pkwt_end_date if current else None)
        if end is not None and join is not None and end < join:
            raise ValidationError("Akhir PKWT tidak boleh sebelum tanggal bergabung.")
        if "photo_file_id" in out:
            file_id = out.pop("photo_file_id")
            if file_id is None:
                out["photo_path"] = None
            else:
                key = await self.repo.image_key(file_id)
                if key is None:
                    raise ValidationError("Foto belum diunggah atau bukan gambar.")
                out["photo_path"] = key
        return out

    async def next_employee_no(self) -> str:
        """Usulan nomor berikutnya: awalan dan lebar angka dari karyawan terbaru, angka = maksimum awalan itu + 1."""
        nos = await self.repo.recent_employee_nos()
        parsed = [m for m in (re.fullmatch(r"(.*?)(\d+)", n) for n in nos) if m]
        if not parsed:
            return "EMP-001"
        prefix, digits = parsed[0].group(1), parsed[0].group(2)
        highest = max(int(m.group(2)) for m in parsed if m.group(1) == prefix)
        return f"{prefix}{highest + 1:0{len(digits)}d}"

    async def create(self, data: EmployeeCreate, user: CurrentUser | None = None) -> dict[str, Any]:
        if user is not None:  # HR/Finance: karyawan baru hanya di kantor jangkauannya (ADR 0002)
            await ensure_office_in_scope(self.repo.db, user, Permission.MANAGE_USERS, data.office_id, "Kantor")
        fields = await self._validate(data.model_dump(exclude={"address"}))
        fields.setdefault("photo_path", None)
        employee_id = await self.repo.insert(fields)
        if data.address:
            await self.repo.add_address(employee_id, data.address.model_dump())
        await self._audit(user, "EMPLOYEE_CREATE", employee_id, None, await self.get(employee_id))
        return await self.detail(employee_id)

    async def update(self, employee_id: UUID, data: EmployeeUpdate,
                     user: CurrentUser | None = None) -> dict[str, Any]:
        current = await self.get(employee_id)
        if user is not None and data.office_id is not None:  # pindah kantor hanya ke kantor jangkauan (ADR 0002)
            await ensure_office_in_scope(self.repo.db, user, Permission.MANAGE_USERS, data.office_id, "Kantor")
        if current.archived:
            raise AppError("INVALID_STATE", "Karyawan diarsipkan; batalkan arsip dulu.", status=409)
        fields = data.model_dump(exclude_unset=True)
        for required in ("employee_no", "full_name", "office_id", "join_date"):
            if required in fields and fields[required] is None:
                raise ValidationError("No. karyawan, nama, kantor, dan tanggal bergabung tidak boleh dikosongkan.")
        validated = await self._validate(fields, current)
        old_keys = await self.repo.photo_keys(employee_id) if "photo_path" in validated else []
        await self.repo.update(employee_id, validated)
        await release_keys(self.repo.db, old_keys)  # foto lama (semua varian) hilang bila tak dipakai lagi
        await self._audit(user, "EMPLOYEE_UPDATE", employee_id, current, await self.get(employee_id),
                          skip_if_empty=True)
        return await self.detail(employee_id)

    async def set_own_photo(self, user: CurrentUser, file_id: UUID | None) -> UUID | None:
        """Karyawan mengganti/menghapus foto profilnya sendiri (HR/Super Admin mengubah orang lain lewat PUT /{id})."""
        if not user.employee_id:
            raise ForbiddenError("Akun ini tidak tertaut ke data karyawan.")
        employee_id = UUID(str(user.employee_id))
        key: str | None = None
        if file_id is not None:
            key = await self.repo.uploaded_image_key(file_id, user.user_id)
            if key is None:
                raise ValidationError("Foto harus berupa gambar yang Anda unggah sendiri.")
        old_keys = await self.repo.photo_keys(employee_id)
        await self.repo.update(employee_id, {"photo_path": key})
        await release_keys(self.repo.db, old_keys)
        return await self.repo.profile_photo_file_id(employee_id)

    # ── Alamat ────────────────────────────────────────────────────────────────
    async def add_address(self, employee_id: UUID, data: AddressIn) -> Any:
        await self.get(employee_id)
        return await self.repo.add_address(employee_id, data.model_dump())

    async def update_address(self, employee_id: UUID, address_id: UUID, data: AddressIn) -> Any:
        row = await self.repo.update_address(employee_id, address_id, data.model_dump())
        if row is None:
            raise NotFoundError("Alamat")
        return row

    async def delete_address(self, employee_id: UUID, address_id: UUID) -> None:
        if not await self.repo.delete_address(employee_id, address_id):
            raise NotFoundError("Alamat")

    # ── Arsip ─────────────────────────────────────────────────────────────────
    async def archive(self, employee_id: UUID, user: CurrentUser | None = None) -> dict[str, Any]:
        employee = await self.repo.lock(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if employee.deleted:
            raise AppError("INVALID_STATE", "Karyawan sudah diarsipkan.", status=409)
        if employee.offboarding_status != "offboarded":
            raise AppError("INVALID_STATE", "Selesaikan dulu proses keluar karyawan ini.", status=409)
        await self.repo.archive(employee_id)
        await self._audit(user, "EMPLOYEE_ARCHIVE", employee_id)
        return {"id": str(employee_id), "message": ARCHIVED}

    async def delete(self, employee_id: UUID, actor: CurrentUser) -> None:
        """Hapus permanen — hanya karyawan yang sudah diarsipkan (cegah salah hapus yang aktif)."""
        employee = await self.repo.lock(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if not employee.deleted:
            raise AppError("NOT_ARCHIVED", "Arsipkan karyawan ini dulu sebelum menghapus permanen.", status=409)
        keys = await employee_keys(self.repo.db, employee_id)  # semua berkas pribadi, sebelum barisnya hilang
        await self.repo.clear_face_embedding(employee_id)
        await self.repo.hard_delete(employee_id)
        released = await release_keys(self.repo.db, keys)  # objek + varian dihapus SETELAH commit
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id,
            actor_role=actor.role,
            actor_email=actor.email, entity_type="employee", entity_id=employee_id,
        )
        logger.info("Hapus permanen karyawan: %d berkas dijadwalkan dihapus", released)

    async def restore(self, employee_id: UUID, user: CurrentUser | None = None) -> dict[str, Any]:
        employee = await self.repo.lock(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if not employee.deleted:
            raise AppError("INVALID_STATE", "Karyawan tidak diarsipkan.", status=409)
        await self.repo.restore(employee_id)
        await self._audit(user, "EMPLOYEE_RESTORE", employee_id)
        return {"id": str(employee_id), "message": RESTORED}
