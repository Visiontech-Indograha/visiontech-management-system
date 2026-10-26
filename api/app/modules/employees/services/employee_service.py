"""
app/modules/employees/services/employee_service.py
Karyawan V2 (Milestone 10).

- Baca: semua yang login (`view:users`, direktori). Kelola: HR (`manage:users`).
- No. karyawan unik; kantor wajib ada; divisi & jabatan aktif; jabatan per divisi harus sama dengan divisi karyawan;
  akhir PKWT ≥ tanggal bergabung; foto = berkas gambar yang sudah diunggah.
- Masa kerja diakhiri lewat modul offboarding (clearance aset), bukan di sini. Arsip hanya untuk yang sudah offboarded.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import AppError, NotFoundError, ValidationError
from app.core.hard_delete import write_delete_audit
from app.core.security import CurrentUser
from app.core.storage import delete_object
from app.modules.employees.repositories.employee_repository import EmployeeRepository
from app.modules.employees.schemas.employee_schema import AddressIn, EmployeeCreate, EmployeeUpdate

ARCHIVED = "Karyawan diarsipkan. Data historis tetap tersimpan."
RESTORED = "Arsip dibatalkan. Karyawan tetap berstatus selesai bekerja."


class EmployeeService:
    def __init__(self, repo: EmployeeRepository) -> None:
        self.repo = repo

    async def list(self, *, page: int, size: int, status: str | None, division_id: UUID | None,
                   office_id: UUID | None, position_id: UUID | None, q: str | None) -> tuple[list[Any], int]:
        filters = {"status": status, "division_id": division_id, "office_id": office_id,
                   "position_id": position_id, "q": (q or "").strip() or None}
        return await self.repo.page(size, (page - 1) * size, **filters), await self.repo.count(**filters)

    async def get(self, employee_id: UUID) -> Any:
        row = await self.repo.get(employee_id)
        if row is None:
            raise NotFoundError("Karyawan")
        return row

    async def detail(self, employee_id: UUID) -> dict[str, Any]:
        row = await self.get(employee_id)
        return {**dict(row._mapping), "addresses": [dict(a._mapping) for a in await self.repo.addresses(employee_id)]}

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

    async def create(self, data: EmployeeCreate) -> dict[str, Any]:
        fields = await self._validate(data.model_dump(exclude={"address"}))
        fields.setdefault("photo_path", None)
        employee_id = await self.repo.insert(fields)
        if data.address:
            await self.repo.add_address(employee_id, data.address.model_dump())
        return await self.detail(employee_id)

    async def update(self, employee_id: UUID, data: EmployeeUpdate) -> dict[str, Any]:
        current = await self.get(employee_id)
        if current.archived:
            raise AppError("INVALID_STATE", "Karyawan diarsipkan; batalkan arsip dulu.", status=409)
        fields = data.model_dump(exclude_unset=True)
        for required in ("employee_no", "full_name", "office_id", "join_date"):
            if required in fields and fields[required] is None:
                raise ValidationError("No. karyawan, nama, kantor, dan tanggal bergabung tidak boleh dikosongkan.")
        await self.repo.update(employee_id, await self._validate(fields, current))
        return await self.detail(employee_id)

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
    async def archive(self, employee_id: UUID) -> dict[str, Any]:
        employee = await self.repo.lock(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if employee.deleted:
            raise AppError("INVALID_STATE", "Karyawan sudah diarsipkan.", status=409)
        if employee.offboarding_status != "offboarded":
            raise AppError("INVALID_STATE", "Selesaikan dulu proses keluar karyawan ini.", status=409)
        await self.repo.archive(employee_id)
        return {"id": str(employee_id), "message": ARCHIVED}

    async def delete(self, employee_id: UUID, actor: CurrentUser) -> None:
        """Hapus permanen — hanya karyawan yang sudah diarsipkan (cegah salah hapus yang aktif)."""
        employee = await self.repo.lock(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if not employee.deleted:
            raise AppError("NOT_ARCHIVED", "Arsipkan karyawan ini dulu sebelum menghapus permanen.", status=409)
        photo_keys = await self.repo.photo_keys(employee_id)
        await self.repo.hard_delete(employee_id)
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id,
            actor_role=actor.role,
            actor_email=actor.email, entity_type="employee", entity_id=employee_id,
        )
        for key in photo_keys:
            delete_object(key)

    async def restore(self, employee_id: UUID) -> dict[str, Any]:
        employee = await self.repo.lock(employee_id)
        if employee is None:
            raise NotFoundError("Karyawan")
        if not employee.deleted:
            raise AppError("INVALID_STATE", "Karyawan tidak diarsipkan.", status=409)
        await self.repo.restore(employee_id)
        return {"id": str(employee_id), "message": RESTORED}
