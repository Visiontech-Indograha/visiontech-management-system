"""Rute dokumen kendaraan (STNK, KIR, pajak, asuransi) dan pengemudi. Izin: view/manage:vehicle_documents
(HSE, OM, SUPER_ADMIN); `/vehicle-documents/mine` untuk karyawan pengemudi (hanya kendaraannya)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_current_user, require_permission
from app.core.list_params import ListParams, apply_list
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.vehicle_documents.dependencies import get_vehicle_document_service
from app.modules.vehicle_documents.schemas.vehicle_document import (
    DocumentTypeOut,
    VehicleDocumentCreate,
    VehicleDocumentOut,
    VehicleDriverCreate,
    VehicleDriverOut,
)
from app.modules.vehicle_documents.services.vehicle_document_service import VehicleDocumentService

router = APIRouter(tags=["Dokumen kendaraan"])

_VIEW = Depends(require_permission(Permission.VIEW_VEHICLE_DOCUMENTS))
_MANAGE = Depends(require_permission(Permission.MANAGE_VEHICLE_DOCUMENTS))


def _docs(rows: list[Any], params: ListParams, response: Response) -> list[VehicleDocumentOut]:
    page = apply_list(
        rows, params, response, lambda r: (r.number_plate, r.vehicle_name, r.doc_type_name, r.doc_no), prefix=True
    )
    return [VehicleDocumentOut.model_validate(r, from_attributes=True) for r in page]


@router.get("/vehicle-documents/types", response_model=list[DocumentTypeOut])
async def list_types(
    _: CurrentUser = _VIEW, service: VehicleDocumentService = Depends(get_vehicle_document_service)
) -> list[DocumentTypeOut]:
    """Jenis dokumen yang aktif (STNK, KIR, pajak, SIM, asuransi)."""
    return [DocumentTypeOut.model_validate(r, from_attributes=True) for r in await service.types()]


@router.get("/vehicle-documents", response_model=list[VehicleDocumentOut])
async def list_documents(
    response: Response,
    vehicle_id: UUID | None = None,
    history: bool = Query(False, description="Sertakan dokumen yang sudah diganti"),
    params: ListParams = Depends(),
    user: CurrentUser = _VIEW,
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> list[VehicleDocumentOut]:
    """Dokumen kendaraan di kantor yang boleh dilihat. Cari `q` = awalan nomor polisi/nama/jenis/nomor dokumen."""
    return _docs(await service.list_documents(user, vehicle_id, history, None), params, response)


@router.get("/vehicle-documents/expiring", response_model=list[VehicleDocumentOut])
async def list_expiring(
    response: Response,
    days: int = Query(30, ge=1, le=90, description="Jatuh tempo dalam N hari (yang sudah lewat ikut)"),
    params: ListParams = Depends(),
    user: CurrentUser = _VIEW,
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> list[VehicleDocumentOut]:
    """Dokumen berlaku yang akan atau sudah jatuh tempo, terdekat dulu."""
    return _docs(await service.list_documents(user, None, False, days), params, response)


@router.get("/vehicle-documents/mine", response_model=list[VehicleDocumentOut])
async def list_mine(
    response: Response,
    params: ListParams = Depends(),
    user: CurrentUser = Depends(get_current_user),
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> list[VehicleDocumentOut]:
    """Dokumen berlaku kendaraan yang sedang dikemudikan akun ini."""
    return _docs(await service.mine(user), params, response)


@router.post("/vehicles/{vehicle_id}/documents", response_model=VehicleDocumentOut, status_code=201)
async def create_document(
    vehicle_id: UUID,
    data: VehicleDocumentCreate,
    user: CurrentUser = _MANAGE,
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> VehicleDocumentOut:
    """Catat dokumen baru; dokumen berlaku sejenis menjadi `replaced` dan berhenti diingatkan."""
    return VehicleDocumentOut.model_validate(await service.create(user, vehicle_id, data), from_attributes=True)


@router.get("/vehicles/{vehicle_id}/drivers", response_model=list[VehicleDriverOut])
async def list_drivers(
    vehicle_id: UUID, user: CurrentUser = _VIEW,
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> list[VehicleDriverOut]:
    return [VehicleDriverOut.model_validate(r, from_attributes=True) for r in await service.drivers(user, vehicle_id)]


@router.post("/vehicles/{vehicle_id}/drivers", response_model=list[VehicleDriverOut], status_code=201)
async def add_driver(
    vehicle_id: UUID, data: VehicleDriverCreate, user: CurrentUser = _MANAGE,
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> list[VehicleDriverOut]:
    """Tambah pengemudi (karyawan kantor yang sama). Sudah aktif = 409."""
    rows = await service.add_driver(user, vehicle_id, data.employee_id)
    return [VehicleDriverOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/vehicles/{vehicle_id}/drivers/{driver_id}/end", response_model=list[VehicleDriverOut])
async def end_driver(
    vehicle_id: UUID, driver_id: UUID, user: CurrentUser = _MANAGE,
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> list[VehicleDriverOut]:
    """Akhiri penugasan pengemudi (hari ini)."""
    rows = await service.end_driver(user, vehicle_id, driver_id)
    return [VehicleDriverOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/vehicle-documents/cron/remind")
async def cron_remind(
    dry_run: bool = False,
    _: CurrentUser = Depends(require_permission(Permission.RUN_SYSTEM_JOBS)),
    service: VehicleDocumentService = Depends(get_vehicle_document_service),
) -> dict[str, Any]:
    """Pemicu manual pengingat dokumen (sama dengan `python -m app.cli pengingat-dokumen`); aman diulang."""
    return await service.run_reminders(dry_run)
