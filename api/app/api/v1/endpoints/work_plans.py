from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_with_user,
    get_plan_assignment_service,
    plan_access,
    plan_day_access,
    require_permission,
)
from app.core.enums import PlanStatus
from app.core.errors import ValidationError, trigger_rule_error
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.crud.crud_plan_access import CRUDPlanAccess
from app.schemas.plan import (
    AssignmentEmployeeOption,
    DayPlanRequest,
    PlanAssignmentOptions,
    PlanDayCreate,
    PlanDayResponse,
    PlanTaskCreate,
    PlanTaskResponse,
    WorkPlanCreate,
    WorkPlanResponse,
    WorkPlanUpdate,
)
from app.services.access_service import (
    PlanAccess,
    PlanNeed,
    check_unit_manager,
    ensure_same_org,
    require_plan_status,
)
from app.services.plan_assignment_service import PlanAssignmentService

router = APIRouter(prefix="/work-plans", tags=["Work Plans"])  # jalur dok 05 §3.3 (V-16)
_VIEW_ACCESS = Depends(plan_access(PlanNeed.VIEW))
_PM_UNIT_ACCESS = Depends(plan_access(PlanNeed.PM_UNIT))
_DAY_PM_UNIT_ACCESS = Depends(plan_day_access(PlanNeed.PM_UNIT))


@router.get("/assignment-options", response_model=PlanAssignmentOptions)
async def assignment_options(
    period_start: date = Query(...),
    period_end: date = Query(...),
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    plan_assignment_service: PlanAssignmentService = Depends(get_plan_assignment_service),
) -> PlanAssignmentOptions:
    """Pilihan PM/personel yang sah untuk periode SK baru (R-23)."""
    values = await plan_assignment_service.options(current_user, period_start, period_end)
    return PlanAssignmentOptions(
        can_choose_pm=values["can_choose_pm"],
        fixed_pm_employee_id=values["fixed_pm_employee_id"],
        fixed_unit_id=values["fixed_unit_id"],
        pm_options=[AssignmentEmployeeOption(**row._mapping) for row in values["pm_options"]],
        personnel_options=[AssignmentEmployeeOption(**row._mapping) for row in values["personnel_options"]],
    )

@router.get("", response_model=list[WorkPlanResponse])
async def get_plans(
    status_filter: str | None = None,
    archived: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
) -> list[WorkPlanResponse]:
    """Hanya SK yang terlihat oleh pengguna (V-07, `domain.js` visiblePlans). `archived=true`: draf
    terarsip — hanya untuk pengelola (V-21)."""
    rows = await CRUDPlanAccess(db).visible_plans(current_user.organization_id, current_user.user_id,
                                                  status_filter, archived)
    return [WorkPlanResponse(**row._mapping) for row in rows]

@router.get("/{plan_id}", response_model=WorkPlanResponse)
async def get_plan(access: PlanAccess = _VIEW_ACCESS) -> WorkPlanResponse:
    return WorkPlanResponse(**access.plan._mapping)

@router.post("", response_model=WorkPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: WorkPlanCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    db: AsyncSession = Depends(get_db_with_user),
    plan_assignment_service: PlanAssignmentService = Depends(get_plan_assignment_service)
) -> WorkPlanResponse:
    await check_unit_manager(db, data.unit_id, current_user)
    await ensure_same_org(db, current_user.organization_id, sites=[data.site_id],
                          employees=[data.pm_employee_id, data.leader_employee_id])
    assignments = plan_assignment_service
    await assignments.validate_owner(current_user, data.unit_id, data.pm_employee_id)
    if data.leader_employee_id:
        await assignments.validate_team_scope(current_user, data.unit_id, [data.leader_employee_id])
    query = text("""
        INSERT INTO vms.work_plan (
            organization_id, unit_id, site_id, title, location_text, description,
            period, pm_employee_id, leader_employee_id, status
        ) VALUES (
            :org, :unit, :site, :title, :loc, :desc, 
            daterange(:start, :end, '[]'), :pm, :leader, 'DRAFT'
        ) RETURNING id, number, status, revision, row_version, cancellation_reason
    """)
    try:
        res = await db.execute(query, {
            "org": current_user.organization_id,
            "unit": data.unit_id, "site": data.site_id,
            "title": data.title, "loc": data.location_text, "desc": data.description,
            "start": data.period_start, "end": data.period_end,
            "pm": data.pm_employee_id, "leader": data.leader_employee_id
        })
        row = res.one()

        # Tambahkan Leader ke tabel work_plan_member secara otomatis
        if data.leader_employee_id:
            add_member = text("""
                INSERT INTO vms.work_plan_member (
                    work_plan_id, employee_id, role_in_plan, valid_period
                ) VALUES (
                    :plan, :emp, 'LEADER', daterange(CAST(:start AS date), NULL, '[)')  -- terbuka = aktif (is_plan_member)
                )
            """)
            await db.execute(add_member, {
                "plan": row.id, "emp": data.leader_employee_id,
                "start": data.period_start, "end": data.period_end
            })
            
        return WorkPlanResponse(
            **data.model_dump(),
            id=row.id, number=row.number, status=row.status,
            revision=row.revision, row_version=row.row_version,
            cancellation_reason=row.cancellation_reason
        )
    except IntegrityError as e:
        # Aturan dari trigger (mis. bentrok jadwal ketua) sampai ke pengguna; sisanya tetap DB_ERROR.
        rule = trigger_rule_error(e)
        if rule:
            raise rule from None
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": str(e)})

@router.patch("/{plan_id}", response_model=WorkPlanResponse)  # EDIT_DRAFT (dok 05)
async def update_plan(
    plan_id: UUID,
    data: WorkPlanUpdate,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user),
    plan_assignment_service: PlanAssignmentService = Depends(get_plan_assignment_service)
) -> WorkPlanResponse:
    current_user = access.user
    await ensure_same_org(db, current_user.organization_id, sites=[data.site_id], employees=[data.leader_employee_id])
    # Optimistic locking
    check = text("SELECT status, row_version, pm_employee_id, leader_employee_id, lower(period) as period_start, upper(period) - integer '1' as period_end, unit_id FROM vms.work_plan WHERE id = :id AND organization_id = :org")
    row = (await db.execute(check, {"id": plan_id, "org": current_user.organization_id})).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="SK tidak ditemukan.")
        
    if row.status != 'DRAFT':
        raise HTTPException(status_code=400, detail={"code": "NOT_DRAFT", "message": "Hanya SK berstatus DRAFT yang dapat diubah."})
        
    if row.row_version != data.row_version:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Dokumen ini telah diubah oleh orang lain. Silakan muat ulang halaman."})
        
    # Update
    updates = []
    params = {"id": plan_id, "org": current_user.organization_id, "version": data.row_version}
    
    if data.title is not None:
        updates.append("title = :title")
        params["title"] = data.title
    if data.site_id is not None:
        updates.append("site_id = :site")
        params["site"] = data.site_id
    if data.location_text is not None:
        updates.append("location_text = :loc")
        params["loc"] = data.location_text
    if data.description is not None:
        updates.append("description = :desc")
        params["desc"] = data.description
    
    if data.period_start and data.period_end:
        updates.append("period = daterange(:start, :end, '[]')")
        params["start"] = data.period_start
        params["end"] = data.period_end
        
    if data.leader_employee_id is not None:
        updates.append("leader_employee_id = :leader")
        params["leader"] = data.leader_employee_id
        
        if data.leader_employee_id != row.leader_employee_id:
            # R-26: ketua baru melewati aturan yang sama dengan buat SK / simpan tim (staf lapangan, unit PM).
            await plan_assignment_service.validate_team_scope(
                current_user, row.unit_id, [data.leader_employee_id])
            # Hapus leader lama jika ada
            await db.execute(text("DELETE FROM vms.work_plan_member WHERE work_plan_id = :plan AND role_in_plan = 'LEADER'"), {"plan": plan_id})
            # Tambahkan leader baru
            add_member = text("""
                INSERT INTO vms.work_plan_member (
                    work_plan_id, employee_id, role_in_plan, valid_period
                ) VALUES (
                    :plan, :emp, 'LEADER', daterange(CAST(:start AS date), NULL, '[)')  -- terbuka = aktif (is_plan_member)
                )
            """)
            start = data.period_start or row.period_start
            end = data.period_end or row.period_end
            try:
                await db.execute(add_member, {
                    "plan": plan_id, "emp": data.leader_employee_id,
                    "start": start, "end": end
                })
            except IntegrityError as exc:
                # Bentrok jadwal ketua (trigger) → 409 berpesan jelas; sebelumnya 500.
                raise trigger_rule_error(exc) or exc from None
            
    updates.append("row_version = row_version + 1")
    
    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan.")
        
    query = text(f"""
        UPDATE vms.work_plan SET {", ".join(updates)} 
        WHERE id = :id AND organization_id = :org AND row_version = :version
        RETURNING id, unit_id, site_id, number, title, location_text, description,
                  lower(period) as period_start, upper(period) - integer '1' as period_end,
                  status, pm_employee_id, leader_employee_id, revision, row_version,
                  cancellation_reason
    """)
    res = await db.execute(query, params)
    updated = res.fetchone()
    
    if not updated:
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Gagal update, kemungkinan data diubah secara bersamaan."})
        
    return WorkPlanResponse(**updated._mapping)

@router.post("/{plan_id}/days", response_model=PlanDayResponse)
async def add_day(
    plan_id: UUID,
    data: PlanDayCreate,
    access: PlanAccess = _PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> PlanDayResponse:
    current_user = access.user
    # Verifikasi status DRAFT
    check = text("SELECT status FROM vms.work_plan WHERE id = :id AND organization_id = :org")
    status_val = (await db.execute(check, {"id": plan_id, "org": current_user.organization_id})).scalar()
    if not status_val or status_val != 'DRAFT':
        raise HTTPException(status_code=400, detail="Tidak dapat menambah hari. Status SK bukan DRAFT.")
        
    insert_day = text("""
        INSERT INTO vms.work_plan_day (work_plan_id, work_date, title, sort_order)
        VALUES (:plan, :date, :title, :sort)
        RETURNING id
    """)
    try:
        res = await db.execute(insert_day, {
            "plan": plan_id, "date": data.work_date,
            "title": data.title, "sort": data.sort_order
        })
        day_id = res.scalar_one()
        return PlanDayResponse(id=day_id, work_plan_id=plan_id, **data.model_dump())
    except Exception:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": "Gagal menambahkan hari (mungkin tanggal bentrok)."})

@router.post("/{plan_id}/days/{day_id}/tasks", response_model=PlanTaskResponse)
async def add_task(
    plan_id: UUID,
    day_id: UUID,
    data: PlanTaskCreate,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> PlanTaskResponse:
    insert_task = text("""
        INSERT INTO vms.work_plan_task (work_plan_day_id, title, sort_order)
        VALUES (:day, :title, :sort)
        RETURNING id
    """)
    res = await db.execute(insert_task, {
        "day": day_id, "title": data.title, "sort": data.sort_order
    })
    task_id = res.scalar_one()
    return PlanTaskResponse(id=task_id, work_plan_day_id=day_id, is_done=False, **data.model_dump())






@router.put("/{plan_id}/days/{day_id}/plan")
async def save_day(
    plan_id: UUID,
    day_id: UUID,
    data: DayPlanRequest,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    db: AsyncSession = Depends(get_db_with_user)
) -> dict[str, object]:
    """domain.js SAVE_DAY (V-23): PM menyusun ulang judul & tugas satu hari selagi SK masih draf."""
    require_plan_status(access, PlanStatus.DRAFT)
    if not 1 <= len(data.tasks) <= 30:
        raise ValidationError("Isi antara 1 sampai 30 tugas per hari.")
    titles = [t.title.strip() for t in data.tasks]
    if not data.title.strip() or not all(titles):
        raise ValidationError("Judul hari dan setiap tugas wajib diisi.")
    await db.execute(text("UPDATE vms.work_plan_day SET title = :title WHERE id = :day"),
                     {"title": data.title.strip(), "day": day_id})
    await db.execute(text("DELETE FROM vms.work_plan_task WHERE work_plan_day_id = :day"), {"day": day_id})
    for order, title in enumerate(titles):
        await db.execute(text("INSERT INTO vms.work_plan_task (work_plan_day_id, title, sort_order) "
                              "VALUES (:day, :title, :sort)"), {"day": day_id, "title": title, "sort": order})
    return {"id": str(day_id), "title": data.title.strip(), "tasks": titles}
