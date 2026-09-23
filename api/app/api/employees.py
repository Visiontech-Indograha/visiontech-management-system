from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from uuid import UUID

from app.api.deps import CurrentUser, get_current_user, get_db_with_user, require_permission
from app.core.permissions import Permission
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    EmployeeAssignmentCreate, EmployeeAssignmentResponse, EmployeeOffboard
)

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("", response_model=EmployeeListResponse)
async def get_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    q: Optional[str] = None,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    offset = (page - 1) * size
    where_clauses = ["organization_id = :org"]
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
    
    items = []
    for row in rows:
        items.append(EmployeeResponse(
            id=row.id, employee_no=row.employee_no, full_name=row.full_name,
            position=row.position, unit_id=row.unit_id, email=row.email,
            phone=row.phone, join_date=row.join_date, birth_date=row.birth_date,
            address=row.address, emergency_contact=row.emergency_contact,
            is_active=row.is_active, offboarded_at=row.offboarded_at,
            offboarding_reason=row.offboarding_reason
        ))
        
    return EmployeeListResponse(items=items, total=total, page=page, size=size)

@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
):
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
        row = res.fetchone()
        
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
):
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

@router.post("/{emp_id}/assignments", response_model=EmployeeAssignmentResponse)
async def add_assignment(
    emp_id: UUID,
    data: EmployeeAssignmentCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    """Mutasi atau Promosi (mengubah unit/jabatan)."""
    # 1. Pastikan karyawan milik org ini
    check = text("SELECT id FROM vms.employee WHERE id = :id AND organization_id = :org")
    if not (await db.execute(check, {"id": emp_id, "org": current_user.organization_id})).scalar():
        raise HTTPException(status_code=404, detail="Karyawan tidak ditemukan.")
        
    # 2. Tutup assignment sebelumnya
    close_prev = text("""
        UPDATE vms.employee_assignment 
        SET valid_to = :start_date 
        WHERE employee_id = :emp_id AND valid_to IS NULL
    """)
    await db.execute(close_prev, {"start_date": data.valid_from, "emp_id": emp_id})
    
    # 3. Insert assignment baru
    insert_asg = text("""
        INSERT INTO vms.employee_assignment (employee_id, position, unit_id, valid_from)
        VALUES (:emp_id, :pos, :unit, :start_date)
        RETURNING id, valid_to
    """)
    res = await db.execute(insert_asg, {
        "emp_id": emp_id, "pos": data.position, 
        "unit": data.unit_id, "start_date": data.valid_from
    })
    row = res.fetchone()
    
    # 4. Sinkronisasi ke master employee
    sync_emp = text("""
        UPDATE vms.employee SET position = :pos, unit_id = :unit 
        WHERE id = :emp_id
    """)
    await db.execute(sync_emp, {"pos": data.position, "unit": data.unit_id, "emp_id": emp_id})
    
    return EmployeeAssignmentResponse(
        id=row.id, employee_id=emp_id, position=data.position,
        unit_id=data.unit_id, valid_from=data.valid_from, valid_to=row.valid_to
    )

@router.post("/{emp_id}/offboard")
async def offboard_employee(
    emp_id: UUID,
    data: EmployeeOffboard,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    db: AsyncSession = Depends(get_db_with_user)
):
    offboard = text("""
        UPDATE vms.employee 
        SET is_active = false, offboarded_at = now(), offboarding_reason = :reason
        WHERE id = :id AND organization_id = :org AND is_active = true
        RETURNING id
    """)
    res = await db.execute(offboard, {"reason": data.reason, "id": emp_id, "org": current_user.organization_id})
    if not res.scalar():
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE", "message": "Gagal offboard (sudah offboard atau tidak ditemukan)."})
        
    # Jika ada app_user, nonaktifkan akunnya
    off_user = text("UPDATE vms.app_user SET is_active = false WHERE employee_id = :emp_id")
    await db.execute(off_user, {"emp_id": emp_id})
    
    return {"message": "Karyawan berhasil dioffboard."}

@router.get("/{emp_id}/conflicts")
async def check_conflicts(
    emp_id: UUID,
    start_date: date,
    end_date: date,
    exclude_plan: Optional[UUID] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    """Mengecek bentrok jadwal (P3-6). Mengembalikan daftar SK yang bentrok."""
    query = text("""
        SELECT work_plan_id, number, title 
        FROM vms.personnel_conflict(:emp, daterange(:start, :end, '[]'), :exclude)
    """)
    rows = (await db.execute(query, {
        "emp": emp_id, "start": start_date, "end": end_date, "exclude": exclude_plan
    })).fetchall()
    
    conflicts = [{"id": r.work_plan_id, "number": r.number, "title": r.title} for r in rows]
    return {"conflicts": conflicts, "has_conflict": len(conflicts) > 0}
