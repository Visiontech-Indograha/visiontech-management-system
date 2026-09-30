from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, ensure_same_org, get_db_with_user, require_permission
from app.core.errors import AppError
from app.core.permissions import Permission
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
    db: AsyncSession = Depends(get_db_with_user)
) -> EmployeeListResponse:
    offset = (page - 1) * size
    where_clauses = ["organization_id = :org", "deleted_at IS NULL"]  # karyawan terhapus disembunyikan (V-29)
    params = {"org": current_user.organization_id, "limit": size, "offset": offset}
    
    if is_active is not None:
        where_clauses.append("is_active = :is_active")
        params["is_active"] = is_active
        
    if q:
        where_clauses.append("(full_name ILIKE :q OR employee_no ILIKE :q)")
        params["q"] = f"%{q}%"
        
    where_str = " AND ".join(where_clauses)
    
    count_query = text(f"SELECT COUNT(*) FROM vms.employee WHERE {where_str}")
    total = (await db.execute(count_query, params)).scalar() or 0
    
    query = text(f"""
        SELECT id, employee_no, full_name, position, unit_id, email, phone, 
               join_date, birth_date, address, emergency_contact, 
               is_active, offboarded_at, offboarding_reason
        FROM vms.employee
        WHERE {where_str}
        ORDER BY full_name ASC
        LIMIT :limit OFFSET :offset
    """)
    rows = (await db.execute(query, params)).fetchall()
    
    scope = await EmployeeService(db).private_viewer(current_user.user_id, current_user.permissions)
    items = []
    for row in rows:
        items.append(_shown(EmployeeResponse(
            id=row.id, employee_no=row.employee_no, full_name=row.full_name,
            position=row.position, unit_id=row.unit_id, email=row.email,
            phone=row.phone, join_date=row.join_date, birth_date=row.birth_date,
            address=row.address, emergency_contact=row.emergency_contact,
            is_active=row.is_active, offboarded_at=row.offboarded_at,
            offboarding_reason=row.offboarding_reason
        ), scope))
        
    return EmployeeListResponse(items=items, total=total, page=page, size=size)

@router.get("/{emp_id}", response_model=EmployeeResponse)
async def get_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> EmployeeResponse:
    """Satu karyawan (tautan langsung /directory/{id}); karyawan organisasi lain/terhapus → 404."""
    row = (await db.execute(text("""
        SELECT id, employee_no, full_name, position, unit_id, email, phone,
               join_date, birth_date, address, emergency_contact,
               is_active, offboarded_at, offboarding_reason
        FROM vms.employee
        WHERE id = :id AND organization_id = :org AND deleted_at IS NULL
    """), {"id": emp_id, "org": current_user.organization_id})).fetchone()
    if row is None:
        raise AppError("NOT_FOUND", "Karyawan tidak ditemukan.", status=404)
    scope = await EmployeeService(db).private_viewer(current_user.user_id, current_user.permissions)
    return _shown(EmployeeResponse(**row._mapping), scope)

@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> EmployeeResponse:
    await ensure_same_org(db, current_user.organization_id, units=[data.unit_id])
    query = text("""
        INSERT INTO vms.employee (
            organization_id, employee_no, full_name, position, unit_id, 
            email, phone, join_date, birth_date, address, emergency_contact
        ) VALUES (
            :org, :eno, :fname, :pos, :unit, :email, :phone, :jdate, :bdate, :addr, :emerg
        ) RETURNING id, is_active, offboarded_at, offboarding_reason
    """)
    try:
        res = await db.execute(query, {
            "org": current_user.organization_id,
            "eno": data.employee_no, "fname": data.full_name, "pos": data.position,
            "unit": data.unit_id, "email": data.email, "phone": data.phone,
            "jdate": data.join_date, "bdate": data.birth_date, "addr": data.address,
            "emerg": data.emergency_contact
        })
        row = res.one()

        # Tambahkan ke employee_assignment perdana
        assign = text("""
            INSERT INTO vms.employee_assignment (employee_id, position, unit_id, valid_from)
            VALUES (:emp_id, :pos, :unit, :jdate)
        """)
        await db.execute(assign, {
            "emp_id": row.id, "pos": data.position, 
            "unit": data.unit_id, "jdate": data.join_date
        })
        
        return EmployeeResponse(
            id=row.id, employee_no=data.employee_no, full_name=data.full_name,
            position=data.position, unit_id=data.unit_id, email=data.email,
            phone=data.phone, join_date=data.join_date, birth_date=data.birth_date,
            address=data.address, emergency_contact=data.emergency_contact,
            is_active=row.is_active, offboarded_at=row.offboarded_at,
            offboarding_reason=row.offboarding_reason
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.put("/{emp_id}", response_model=EmployeeResponse)
async def update_employee(
    emp_id: UUID,
    data: EmployeeUpdate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> EmployeeResponse:
    # Hanya update info pribadi, jabatan diubah via assignment
    updates = []
    params = {"id": emp_id, "org": current_user.organization_id}
    
    for field, value in data.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = :{field}")
        params[field] = value
        
    if not updates:
        raise HTTPException(status_code=400, detail={"code": "NO_UPDATE", "message": "Tidak ada data untuk diubah."})
        
    query = text(f"""
        UPDATE vms.employee SET {", ".join(updates)} 
        WHERE id = :id AND organization_id = :org
        RETURNING *
    """)
    res = await db.execute(query, params)
    row = res.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Karyawan tidak ditemukan."})
        
    return EmployeeResponse(
        id=row.id, employee_no=row.employee_no, full_name=row.full_name,
        position=row.position, unit_id=row.unit_id, email=row.email,
        phone=row.phone, join_date=row.join_date, birth_date=row.birth_date,
        address=row.address, emergency_contact=row.emergency_contact,
        is_active=row.is_active, offboarded_at=row.offboarded_at,
        offboarding_reason=row.offboarding_reason
    )

@router.get("/{emp_id}/assignments", response_model=list[EmployeeAssignmentResponse])
async def list_assignments(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> list[EmployeeAssignmentResponse]:
    """Riwayat jabatan/penempatan (M2), terbaru dulu. Karyawan organisasi lain → 404."""
    rows = await EmployeeService(db).assignments(emp_id, current_user.organization_id)
    return [EmployeeAssignmentResponse(**r._mapping) for r in rows]


@router.post("/{emp_id}/assignments", response_model=EmployeeAssignmentResponse)
async def add_assignment(
    emp_id: UUID,
    data: EmployeeAssignmentCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> EmployeeAssignmentResponse:
    """domain.js PROMOTE — mutasi/promosi; aturan di EmployeeService.promote."""
    await ensure_same_org(db, current_user.organization_id, units=[data.unit_id])
    row = await EmployeeService(db).promote(emp_id, current_user.organization_id, data.position, data.unit_id,
                                            data.valid_from)
    return EmployeeAssignmentResponse(**row._mapping)

@router.post("/{emp_id}/offboard")
async def offboard_employee(
    emp_id: UUID,
    data: EmployeeOffboard,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, Any]:
    """domain.js OFFBOARD: HR mengakhiri masa kerja (tidak boleh saat masih di SK berjalan)."""
    return await EmployeeService(db).offboard(emp_id, current_user.organization_id, data.reason)


@router.post("/{emp_id}/archive")
async def archive_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user),
) -> dict[str, Any]:
    """Hapus karyawan (V-29, keputusan pemilik): hanya yang sudah di-offboard; dibalik lewat /restore."""
    return await EmployeeService(db).archive_employee(emp_id, current_user.organization_id)


@router.post("/{emp_id}/restore")
async def restore_employee(
    emp_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user),
) -> dict[str, Any]:
    """domain.js RESTORE_EMPLOYEE (V-29): HR memulihkan karyawan terhapus sebagai nonaktif."""
    return await EmployeeService(db).restore_employee(emp_id, current_user.organization_id)

@router.get("/{emp_id}/conflicts")
async def check_conflicts(
    emp_id: UUID,
    start_date: date,
    end_date: date,
    exclude_plan: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, Any]:
    """Mengecek bentrok jadwal (P3-6) — untuk penyusun SK (V-09). Karyawan/SK asing → 404."""
    await ensure_same_org(db, current_user.organization_id, employees=[emp_id], work_plans=[exclude_plan])
    query = text("""
        SELECT work_plan_id, number, title 
        FROM vms.personnel_conflict(:emp, daterange(:start, :end, '[]'), :exclude)
    """)
    rows = (await db.execute(query, {
        "emp": emp_id, "start": start_date, "end": end_date, "exclude": exclude_plan
    })).fetchall()
    
    conflicts = [{"id": r.work_plan_id, "number": r.number, "title": r.title} for r in rows]
    return {"conflicts": conflicts, "has_conflict": len(conflicts) > 0}
