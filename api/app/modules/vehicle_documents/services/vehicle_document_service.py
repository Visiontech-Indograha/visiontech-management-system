"""Dokumen kendaraan: daftar, buat/ganti (riwayat), pengemudi. Cakupan kantor: SUPER_ADMIN dan OM semua kantor,
peran lain (HSE) kantornya sendiri; objek di luar cakupan dijawab 404. Karyawan hanya melihat dokumen kendaraan
yang sedang ia kemudikan."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.vehicle_documents.repositories.vehicle_document_repository import VehicleDocumentRepository
from app.modules.vehicle_documents.services import reminder_service

_ALL_OFFICES = ("SUPER_ADMIN", "OPERATIONAL_MANAGER")


def offices_in_scope(user: CurrentUser) -> list[str] | None:
    """None = semua kantor; daftar kosong = tidak ada yang terlihat."""
    if user.has_role(*_ALL_OFFICES):
        return None
    return [user.office_id] if user.office_id else []


def today() -> Any:
    return jakarta_now().date()


class VehicleDocumentService:
    def __init__(self, repo: VehicleDocumentRepository) -> None:
        self.repo = repo

    async def types(self) -> list[Any]:
        return await self.repo.document_types()

    async def list_documents(
        self, user: CurrentUser, vehicle_id: UUID | None, history: bool, due_within: int | None,
        doc_type_code: str | None = None, office_id: UUID | None = None,
    ) -> list[Any]:
        offices = offices_in_scope(user)
        if offices is not None and not offices:
            if office_id:
                raise NotFoundError("Kantor")
            return []
        if office_id:
            if offices is not None and str(office_id) not in offices:
                raise NotFoundError("Kantor")
            offices = [str(office_id)]
        if doc_type_code and not await self.repo.type_exists(doc_type_code):
            raise ValidationError("Jenis dokumen tidak dikenal.")
        if vehicle_id:
            await self._vehicle_in_scope(user, vehicle_id)
        return await self.repo.list_documents(today(), offices, vehicle_id, history, due_within, None, doc_type_code)

    async def mine(self, user: CurrentUser) -> list[Any]:
        if not user.employee_id:
            return []
        return await self.repo.list_documents(today(), None, None, False, None, user.employee_id)

    async def _vehicle_in_scope(self, user: CurrentUser, vehicle_id: UUID) -> Any:
        vehicle = await self.repo.vehicle(vehicle_id)
        offices = offices_in_scope(user)
        if vehicle is None or (offices is not None and str(vehicle.office_id) not in offices):
            raise NotFoundError("Kendaraan")
        return vehicle

    async def create(self, user: CurrentUser, vehicle_id: UUID, data: Any) -> Any:
        vehicle = await self._vehicle_in_scope(user, vehicle_id)
        if await self.repo.type_for_vehicle(data.doc_type_code) is None:
            raise ValidationError("Jenis dokumen tidak dikenal untuk kendaraan.")
        if data.file_id is not None and await self.repo.file_office(data.file_id) != vehicle.office_id:
            raise NotFoundError("Berkas")
        await self.repo.replace_active(vehicle_id, data.doc_type_code)
        new_id = await self.repo.insert(vehicle.office_id, vehicle_id, data.model_dump())
        return await self.repo.get(new_id, today())

    async def drivers(self, user: CurrentUser, vehicle_id: UUID) -> list[Any]:
        await self._vehicle_in_scope(user, vehicle_id)
        return await self.repo.drivers(vehicle_id)

    async def add_driver(self, user: CurrentUser, vehicle_id: UUID, employee_id: UUID) -> list[Any]:
        vehicle = await self._vehicle_in_scope(user, vehicle_id)
        if await self.repo.employee_office(employee_id) != vehicle.office_id:
            raise NotFoundError("Karyawan")
        if await self.repo.add_driver(vehicle.office_id, vehicle_id, employee_id, today()) is None:
            raise ConflictError("Karyawan ini sudah menjadi pengemudi kendaraan tersebut.")
        return await self.repo.drivers(vehicle_id)

    async def end_driver(self, user: CurrentUser, vehicle_id: UUID, driver_id: UUID) -> list[Any]:
        await self._vehicle_in_scope(user, vehicle_id)
        if not await self.repo.end_driver(vehicle_id, driver_id, today()):
            raise NotFoundError("Pengemudi")
        return await self.repo.drivers(vehicle_id)

    async def run_reminders(self, dry_run: bool) -> dict[str, Any]:
        """Pemicu manual pengingat (sama dengan CLI `pengingat-dokumen`); aman diulang."""
        return (await reminder_service.jalankan(self.repo.db, dry_run=dry_run)).as_dict()
