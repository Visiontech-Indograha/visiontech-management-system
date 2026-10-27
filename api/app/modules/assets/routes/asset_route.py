"""
app/modules/assets/routes/asset_route.py

Rute endpoint HTTP inventaris aset (/assets): alat, kendaraan (+ berkas & inspeksi), peminjaman.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.assets.controllers.asset_controller import AssetController
from app.modules.assets.schemas.asset_schema import (
    AssetStatus,
    AssetStatusUpdate,
    InspectionCreate,
    InspectionOut,
    LoanCreate,
    LoanOut,
    LoanRequestCreate,
    LoanRequestOut,
    LoanRequestReview,
    LoanReturn,
    LoanReturnRequest,
    ToolCreate,
    ToolOut,
    ToolUpdate,
    VehicleCreate,
    VehicleFileCreate,
    VehicleFileOut,
    VehicleOut,
    VehicleUpdate,
)

router = APIRouter(prefix="/assets", tags=["Assets"])
_MANAGE = Depends(require_permission(Permission.MANAGE_ASSETS))
_LOGIN = Depends(get_current_user)


# ── Alat ───────────────────────────────────────────────────────────────────────
@router.get("/tools", response_model=list[ToolOut])
async def list_tools(
    office_id: UUID | None = None,
    asset_status: AssetStatus | None = Query(None, alias="status"),
    current_user: CurrentUser = _LOGIN,
    controller: AssetController = Depends(),
) -> list[ToolOut]:
    """Daftar alat (pribadi & umum) beserta pemegangnya saat ini."""
    return await controller.handle_list_tools(office_id, asset_status)


@router.post("/tools", response_model=ToolOut, status_code=status.HTTP_201_CREATED)
async def create_tool(
    data: ToolCreate, current_user: CurrentUser = _MANAGE, controller: AssetController = Depends()
) -> ToolOut:
    """Mendaftarkan alat baru (kode alat unik)."""
    return await controller.handle_create_tool(data)


@router.put("/tools/{tool_id}", response_model=ToolOut)
async def update_tool(
    tool_id: UUID, data: ToolUpdate, current_user: CurrentUser = _MANAGE, controller: AssetController = Depends()
) -> ToolOut:
    """Mengubah data alat (sebagian)."""
    return await controller.handle_update_tool(tool_id, data)


@router.post("/tools/{tool_id}/status", response_model=ToolOut)
async def set_tool_status(
    tool_id: UUID, data: AssetStatusUpdate, current_user: CurrentUser = _MANAGE,
    controller: AssetController = Depends(),
) -> ToolOut:
    """Menandai alat siap/rusak/hilang/pensiun (tidak saat sedang dipinjam)."""
    return await controller.handle_tool_status(tool_id, data.status)


@router.delete("/tools/{tool_id}")
async def delete_tool(
    tool_id: UUID, current_user: CurrentUser = _MANAGE, controller: AssetController = Depends()
) -> dict[str, str]:
    """Menghapus (soft delete) alat yang tidak sedang dipinjam."""
    return await controller.handle_delete("TOOL", tool_id)


# ── Kendaraan ──────────────────────────────────────────────────────────────────
@router.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    office_id: UUID | None = None,
    asset_status: AssetStatus | None = Query(None, alias="status"),
    current_user: CurrentUser = _LOGIN,
    controller: AssetController = Depends(),
) -> list[VehicleOut]:
    """Daftar kendaraan beserta masa berlaku STNK/KIR dan pemegangnya saat ini."""
    return await controller.handle_list_vehicles(office_id, asset_status)


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    data: VehicleCreate, current_user: CurrentUser = _MANAGE, controller: AssetController = Depends()
) -> VehicleOut:
    """Mendaftarkan kendaraan baru (nomor polisi unik)."""
    return await controller.handle_create_vehicle(data)


@router.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: UUID, data: VehicleUpdate, current_user: CurrentUser = _MANAGE,
    controller: AssetController = Depends(),
) -> VehicleOut:
    """Mengubah data kendaraan (sebagian)."""
    return await controller.handle_update_vehicle(vehicle_id, data)


@router.post("/vehicles/{vehicle_id}/status", response_model=VehicleOut)
async def set_vehicle_status(
    vehicle_id: UUID, data: AssetStatusUpdate, current_user: CurrentUser = _MANAGE,
    controller: AssetController = Depends(),
) -> VehicleOut:
    """Menandai kendaraan siap/rusak/hilang/pensiun (tidak saat sedang dipinjam)."""
    return await controller.handle_vehicle_status(vehicle_id, data.status)


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: UUID, current_user: CurrentUser = _MANAGE, controller: AssetController = Depends()
) -> dict[str, str]:
    """Menghapus (soft delete) kendaraan yang tidak sedang dipinjam."""
    return await controller.handle_delete("VEHICLE", vehicle_id)


@router.get("/vehicles/{vehicle_id}/files", response_model=list[VehicleFileOut])
async def list_vehicle_files(
    vehicle_id: UUID, current_user: CurrentUser = _LOGIN, controller: AssetController = Depends()
) -> list[VehicleFileOut]:
    """Berkas kendaraan (STNK, BPKB, KIR)."""
    return await controller.handle_vehicle_files(vehicle_id)


@router.post("/vehicles/{vehicle_id}/files", response_model=list[VehicleFileOut], status_code=201)
async def add_vehicle_file(
    vehicle_id: UUID, data: VehicleFileCreate, current_user: CurrentUser = _MANAGE,
    controller: AssetController = Depends(),
) -> list[VehicleFileOut]:
    """Mencatat berkas kendaraan; berkas sejenis yang lama menjadi `extended`."""
    return await controller.handle_add_vehicle_file(vehicle_id, data)


@router.get("/vehicles/{vehicle_id}/inspections", response_model=list[InspectionOut])
async def list_inspections(
    vehicle_id: UUID, current_user: CurrentUser = _LOGIN, controller: AssetController = Depends()
) -> list[InspectionOut]:
    """Riwayat inspeksi kendaraan (terbaru dulu)."""
    return await controller.handle_inspections(vehicle_id)


@router.post("/vehicles/{vehicle_id}/inspections", response_model=list[InspectionOut], status_code=201)
async def add_inspection(
    vehicle_id: UUID, data: InspectionCreate, current_user: CurrentUser = _LOGIN,
    controller: AssetController = Depends(),
) -> list[InspectionOut]:
    """Mencatat inspeksi kendaraan — pengelola aset atau pemegang kendaraan saat ini."""
    return await controller.handle_add_inspection(current_user, vehicle_id, data)


# ── Peminjaman ────────────────────────────────────────────────────────────────
@router.get("/loans", response_model=list[LoanOut])
async def list_loans(
    open_only: bool = Query(True, alias="open"),
    employee_id: UUID | None = None,
    daily_plan_id: UUID | None = None,
    current_user: CurrentUser = _LOGIN,
    controller: AssetController = Depends(),
) -> list[LoanOut]:
    """Peminjaman aset (default: yang belum dikembalikan). Pekerja lapangan hanya melihat miliknya."""
    return await controller.handle_loans(
        current_user, open_only=open_only, employee_id=employee_id, daily_plan_id=daily_plan_id
    )


@router.post("/loans", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
async def lend_asset(
    data: LoanCreate, current_user: CurrentUser = _MANAGE, controller: AssetController = Depends()
) -> LoanOut:
    """Serah terima aset ke karyawan (opsional dikaitkan ke jadwal harian tim)."""
    return await controller.handle_lend(data)


@router.post("/loans/{assignment_id}/return", response_model=LoanOut)
async def return_asset(
    assignment_id: UUID, data: LoanReturn, current_user: CurrentUser = _MANAGE,
    controller: AssetController = Depends(),
) -> LoanOut:
    """Pengembalian aset dengan kondisinya (ready/damaged/lost)."""
    return await controller.handle_return(assignment_id, data.condition)


# ── Pengajuan pinjam & pengembalian oleh karyawan ─────────────────────────────
@router.get("/loan-requests", response_model=list[LoanRequestOut])
async def list_loan_requests(
    status_filter: str | None = Query(None, alias="status"),
    current_user: CurrentUser = _LOGIN,
    controller: AssetController = Depends(),
) -> list[LoanRequestOut]:
    """Pengajuan pinjam aset. Pengelola aset melihat semua; karyawan hanya miliknya."""
    return await controller.handle_requests(current_user, status_filter)


@router.post("/loan-requests", response_model=LoanRequestOut, status_code=status.HTTP_201_CREATED)
async def request_loan(
    data: LoanRequestCreate, current_user: CurrentUser = _LOGIN, controller: AssetController = Depends()
) -> LoanRequestOut:
    """Karyawan mengajukan pinjam alat atau kendaraan untuk dirinya sendiri."""
    return await controller.handle_request_loan(current_user, data)


@router.post("/loan-requests/{request_id}/cancel", response_model=LoanRequestOut)
async def cancel_loan_request(
    request_id: UUID, current_user: CurrentUser = _LOGIN, controller: AssetController = Depends()
) -> LoanRequestOut:
    """Pemohon membatalkan pengajuan yang masih menunggu."""
    return await controller.handle_cancel_request(current_user, request_id)


@router.post("/loan-requests/{request_id}/review", response_model=LoanRequestOut)
async def review_loan_request(
    request_id: UUID, data: LoanRequestReview, current_user: CurrentUser = _MANAGE,
    controller: AssetController = Depends(),
) -> LoanRequestOut:
    """HR/GA menyetujui (langsung serah terima) atau menolak pengajuan."""
    return await controller.handle_review_request(current_user, request_id, data)


@router.post("/loans/{assignment_id}/return-request", response_model=LoanOut)
async def request_return(
    assignment_id: UUID, data: LoanReturnRequest, current_user: CurrentUser = _LOGIN,
    controller: AssetController = Depends(),
) -> LoanOut:
    """Pemegang aset mengajukan pengembalian dengan kondisi dan foto; pengelola yang mengonfirmasi."""
    return await controller.handle_return_request(current_user, assignment_id, data)
