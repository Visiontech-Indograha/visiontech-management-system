from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_employee_service, require_permission
from app.core.errors import AppError
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.schemas.employee import (
    EmployeeAssignmentCreate,
    EmployeeAssignmentResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeOffboard,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService

PRIVATE_FIELDS = ("email", "phone", "address", "birth_date", "emergency_contact")


def _shown(emp: EmployeeResponse, scope: tuple[bool, str | None]) -> EmployeeResponse:
    """M2-01: data kontak pribadi dikosongkan kecuali untuk HR/admin atau pemiliknya (404-style: tidak dibocorkan)."""
    see_all, own = scope
    if see_all or str(emp.id) == own:
        return emp
    return emp.model_copy(update=dict.fromkeys(PRIVATE_FIELDS))


router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("", response_model=EmployeeListResponse)
async def get_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    q: str | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> EmployeeListResponse:
    """
    Mendapatkan daftar karyawan di organisasi pengguna.
    Mendukung paginasi dan pencarian (berdasarkan nama atau nomor karyawan).

    Query params:
    - page: Halaman (default 1)
    - size: Jumlah per halaman (default 20, max 100)
    - is_active: Filter karyawan aktif/nonaktif
    - q: Kata kunci pencarian nama / NIK

    Return: Daftar karyawan (EmployeeListResponse)
    """
    total, rows = await employee_service.list_page(current_user.organization_id, is_active, q, page, size)
    scope = await employee_service.private_viewer(current_user.user_id, current_user.permissions)
    items = [_shown(EmployeeResponse(**row._mapping), scope) for row in rows]
    return EmployeeListResponse(items=items, total=total, page=page, size=size)

@router.get("/{emp_id}", response_model=EmployeeResponse)
async def get_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> EmployeeResponse:
    """
    Satu karyawan (tautan langsung /directory/{id}); karyawan organisasi lain/terhapus → 404.

    Path params:
    - emp_id: UUID karyawan yang ingin dilihat detailnya

    Return: Detail karyawan (EmployeeResponse)
    """
    row = await employee_service.get(emp_id, current_user.organization_id)
    scope = await employee_service.private_viewer(current_user.user_id, current_user.permissions)
    return _shown(EmployeeResponse(**row._mapping), scope)

@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> EmployeeResponse:
    """
    Menambahkan data karyawan baru ke dalam organisasi.

    Body params:
    - data: Data karyawan baru (EmployeeCreate)

    Return: Detail karyawan yang baru dibuat (EmployeeResponse)
    """
    try:
        row = await employee_service.create(current_user.organization_id, data.model_dump())
    except AppError:
        raise
    except Exception as e:
        # Pesan DB_ERROR diganti teks umum oleh handler galat; isi aslinya hanya ke log (T-06).
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)}) from e
    return EmployeeResponse(**data.model_dump(), id=row.id, is_active=row.is_active,
                            offboarded_at=row.offboarded_at, offboarding_reason=row.offboarding_reason)

@router.put("/{emp_id}", response_model=EmployeeResponse)
async def update_employee(
    emp_id: UUID,
    data: EmployeeUpdate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> EmployeeResponse:
    """
    Mengubah data pribadi karyawan. (Jabatan/unit diubah melalui endpoint /assignments).

    Path params:
    - emp_id: UUID dari karyawan

    Body params:
    - data: Data yang ingin diubah (EmployeeUpdate)

    Return: Detail karyawan yang diperbarui (EmployeeResponse)
    """
    # Hanya data pribadi; jabatan diubah via assignment. attendance_mode wajib: null berarti "tidak diubah".
    fields = {k: v for k, v in data.model_dump(exclude_unset=True).items()
              if not (k == "attendance_mode" and v is None)}
    if not fields:
        raise HTTPException(status_code=400, detail={"code": "NO_UPDATE", "message": "Tidak ada data untuk diubah."})
    row = await employee_service.update(emp_id, current_user.organization_id, fields)
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Karyawan tidak ditemukan."})
    return EmployeeResponse(**row._mapping)

@router.get("/{emp_id}/assignments", response_model=list[EmployeeAssignmentResponse])
async def list_assignments(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> list[EmployeeAssignmentResponse]:
    """
    Riwayat jabatan/penempatan (M2), terbaru dulu. Karyawan organisasi lain → 404.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Daftar mutasi jabatan (list[EmployeeAssignmentResponse])
    """
    # Menggunakan injeksi dependensi EmployeeService untuk mengambil data penugasan
    # Memanggil layer service (employee_service)
    rows = await employee_service.assignments(emp_id, current_user.organization_id)
    return [EmployeeAssignmentResponse(**r._mapping) for r in rows]


@router.post("/{emp_id}/assignments", response_model=EmployeeAssignmentResponse)
async def add_assignment(
    emp_id: UUID,
    data: EmployeeAssignmentCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> EmployeeAssignmentResponse:
    """
    domain.js PROMOTE — mutasi/promosi; aturan di EmployeeService.promote.

    Path params:
    - emp_id: UUID dari karyawan

    Body params:
    - data: Data mutasi/promosi baru (EmployeeAssignmentCreate)

    Return: Riwayat jabatan baru (EmployeeAssignmentResponse)
    """
    # Injeksi database (db) untuk pengecekan referensi organisasi dan employee_service untuk eksekusi
    # Memanggil service layer dengan meneruskan data jabatan yang baru
    await employee_service.ensure_units(current_user.organization_id, data.unit_id)
    row = await employee_service.promote(emp_id, current_user.organization_id, data.position, data.unit_id,
                                            data.valid_from)
    return EmployeeAssignmentResponse(**row._mapping)

@router.post("/{emp_id}/offboard")
async def offboard_employee(
    emp_id: UUID,
    data: EmployeeOffboard,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> dict[str, Any]:
    """
    domain.js OFFBOARD: HR mengakhiri masa kerja (tidak boleh saat masih di SK berjalan).

    Path params:
    - emp_id: UUID dari karyawan

    Body params:
    - data: Data offboard termasuk alasan (EmployeeOffboard)

    Return: Detail hasil proses offboard
    """
    # Memerlukan izin MANAGE_USERS dan dependensi employee_service
    # Meneruskan perintah offboard ke layer service
    return await employee_service.offboard(emp_id, current_user.organization_id, data.reason)


@router.post("/{emp_id}/archive")
async def archive_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service),
) -> dict[str, Any]:
    """
    Hapus karyawan (V-29, keputusan pemilik): hanya yang sudah di-offboard; dibalik lewat /restore.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Detail hasil pengarsipan
    """
    # Mengambil instance EmployeeService dari Depends
    # Melakukan pengarsipan (penghapusan lunak) pada data karyawan melalui service layer
    return await employee_service.archive_employee(emp_id, current_user.organization_id)


@router.post("/{emp_id}/restore")
async def restore_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    employee_service: EmployeeService = Depends(get_employee_service),
) -> dict[str, Any]:
    """
    domain.js RESTORE_EMPLOYEE (V-29): HR memulihkan karyawan terhapus sebagai nonaktif.

    Path params:
    - emp_id: UUID dari karyawan

    Return: Detail hasil pemulihan
    """
    # Menggunakan injeksi dependensi EmployeeService
    # Meneruskan perintah pemulihan (restore) ke service layer
    return await employee_service.restore_employee(emp_id, current_user.organization_id)

@router.get("/{emp_id}/conflicts")
async def check_conflicts(
    emp_id: UUID,
    start_date: date,
    end_date: date,
    exclude_plan: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    employee_service: EmployeeService = Depends(get_employee_service)
) -> dict[str, Any]:
    """Mengecek bentrok jadwal (P3-6) — untuk penyusun SK (V-09). Karyawan/SK asing → 404."""
    rows = await employee_service.conflicts(emp_id, current_user.organization_id, start_date, end_date, exclude_plan)
    conflicts = [{"id": r.work_plan_id, "number": r.number, "title": r.title} for r in rows]
    return {"conflicts": conflicts, "has_conflict": len(conflicts) > 0}
