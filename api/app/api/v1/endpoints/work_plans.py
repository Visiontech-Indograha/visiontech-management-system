from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db_with_user,
    get_plan_assignment_service,
    get_plan_draft_service,
    get_plan_transition_service,
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
from app.schemas.plan_draft import (
    FormAsset,
    FormPerson,
    FormSite,
    PlanDetailOut,
    PlanDraftRequest,
    PlanFormOptions,
)
from app.services.access_service import (
    PlanAccess,
    PlanNeed,
    check_unit_manager,
    ensure_same_org,
    require_plan_status,
)
from app.services.pdf_service import render_plan_preview_html
from app.services.plan_assignment_service import PlanAssignmentService
from app.services.plan_draft_service import PlanDraftService
from app.services.plan_transition_service import PlanTransitionService

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
    """
    Mengambil pilihan PM/personel yang sah untuk periode SK baru (R-23) (GET).
    
    Query Parameters:
    - period_start (date): Tanggal mulai periode SK.
    - period_end (date): Tanggal akhir periode SK.
    
    Returns:
    - PlanAssignmentOptions: Pilihan personil yang dapat ditugaskan.
    """
    # Menggunakan Dependency Injection untuk memeriksa izin CREATE_PLAN (require_permission)
    # Memanggil Service layer untuk mendapatkan daftar pilihan assignment
    values = await plan_assignment_service.options(current_user, period_start, period_end)
    return PlanAssignmentOptions(
        can_choose_pm=values["can_choose_pm"],
        fixed_pm_employee_id=values["fixed_pm_employee_id"],
        fixed_unit_id=values["fixed_unit_id"],
        pm_options=[AssignmentEmployeeOption(**row._mapping) for row in values["pm_options"]],
        personnel_options=[AssignmentEmployeeOption(**row._mapping) for row in values["personnel_options"]],
    )

@router.get("/form-options", response_model=PlanFormOptions)
async def form_options(
    plan_id: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
) -> PlanFormOptions:
    """
    Mengambil pilihan untuk form "Buat SK" pada alur v2 (SK2-A/B) (GET).
    
    Query Parameters:
    - plan_id (UUID | None): ID draf yang sedang diubah (pilihannya ikut tampil).
    
    Returns:
    - PlanFormOptions: Opsi-opsi untuk mengisi form SK.
    """
    # Menggunakan Dependency Injection untuk memastikan izin dan memuat PlanDraftService
    # Memanggil Service layer untuk mengambil seluruh nilai form
    values = await plan_draft_service.form_options(current_user, plan_id)
    return PlanFormOptions(
        unit_name=values["unit_name"], categories=values["categories"],
        sites=[FormSite(**r._mapping) for r in values["sites"]],
        leaders=[FormPerson(**r._mapping) for r in values["leaders"]],
        members=[FormPerson(**r._mapping) for r in values["members"]],
        tools=[FormAsset(**r._mapping) for r in values["tools"]],
        vehicles=[FormAsset(**r._mapping) for r in values["vehicles"]],
    )


@router.get("/driver-options", response_model=list[UUID])
async def driver_options(
    vehicle_id: UUID,
    period_end: date,
    candidate_ids: list[UUID] = Query(default=[]),
    plan_id: UUID | None = None,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
) -> list[str]:
    """
    Mengambil daftar calon pengemudi (driver) yang valid (GET).
    Calon driver dari ketua + anggota terpilih yang ber-SIM sesuai tipe kendaraan dan tidak terikat SK lain.
    
    Query Parameters:
    - vehicle_id (UUID): ID kendaraan.
    - period_end (date): Tanggal akhir periode.
    - candidate_ids (list[UUID]): Daftar ID kandidat.
    - plan_id (UUID | None): ID draf SK terkait jika ada.
    
    Returns:
    - list[str]: Daftar ID calon pengemudi yang valid.
    """
    # Menggunakan Dependency Injection untuk memeriksa hak akses dan mendapatkan PlanDraftService
    # Meneruskan data query param ke fungsi driver_options pada layer Service
    return await plan_draft_service.driver_options(current_user, vehicle_id, candidate_ids, period_end, plan_id)


@router.post("/full", response_model=PlanDetailOut, status_code=status.HTTP_201_CREATED)
async def create_full_plan(
    data: PlanDraftRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
) -> PlanDetailOut:
    """
    Membuat SK lengkap dalam satu transaksi (alur v2) (POST).
    Status SK akan langsung menjadi Draf.
    
    Request Body:
    - data (PlanDraftRequest): Seluruh rincian SK.
    
    Returns:
    - PlanDetailOut: Detail lengkap SK yang baru dibuat.
    """
    # Menggunakan Dependency Injection untuk kontrol hak akses
    # Memanggil service create_plan untuk memproses semua data pembuatan SK sekaligus
    return PlanDetailOut(**await plan_draft_service.create_plan(current_user, data))


@router.get("", response_model=list[WorkPlanResponse])
async def get_plans(
    status_filter: str | None = None,
    archived: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user),
    plan_transition_service: PlanTransitionService = Depends(get_plan_transition_service),
) -> list[WorkPlanResponse]:
    """
    Mengambil daftar SK yang terlihat oleh pengguna (V-07) (GET).
    SK Diterima yang tanggal mulainya tiba dijalankan dulu (alur v2).
    
    Query Parameters:
    - status_filter (str | None): Filter berdasarkan status SK.
    - archived (bool): Menampilkan draf terarsip (hanya untuk pengelola) (V-21).
    
    Returns:
    - list[WorkPlanResponse]: Daftar rencana kerja (SK).
    """
    # Menggunakan Dependency Injection untuk mendapatkan session database (get_db_with_user)
    # serta PlanTransitionService untuk pembaruan status SK otomatis
    await plan_transition_service.start_due_plans(current_user.organization_id)
    # CRUD layer digunakan untuk memuat data SK sesuai permission yang dimiliki user
    rows = await CRUDPlanAccess(db).visible_plans(current_user.organization_id, current_user.user_id,
                                                  status_filter, archived)
    return [WorkPlanResponse(**row._mapping) for row in rows]

@router.get("/{plan_id}", response_model=WorkPlanResponse)
async def get_plan(access: PlanAccess = _VIEW_ACCESS) -> WorkPlanResponse:
    """
    Mengambil data dasar dari sebuah SK (GET).
    
    Path Parameters:
    - plan_id (UUID): ID dari SK (work plan).
    
    Returns:
    - WorkPlanResponse: Data dasar SK.
    """
    # Menggunakan Dependency Injection (_VIEW_ACCESS) untuk mendapatkan data plan yang sudah divalidasi aksesnya
    return WorkPlanResponse(**access.plan._mapping)


@router.get("/{plan_id}/detail", response_model=PlanDetailOut)
async def get_plan_detail(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
) -> PlanDetailOut:
    """
    Mengambil isi lengkap SK: data umum, lokasi, tim, detail pekerjaan per hari, alat & kendaraan (GET).
    
    Path Parameters:
    - plan_id (UUID): ID SK (work plan).
    
    Returns:
    - PlanDetailOut: Detail lengkap dari SK.
    """
    # Dependency Injection memastikan hak akses baca (VIEW) dan menyediakan service layer
    return PlanDetailOut(**await plan_draft_service.detail(plan_id))


@router.put("/{plan_id}/full", response_model=PlanDetailOut)
async def edit_full_plan(
    plan_id: UUID,
    data: PlanDraftRequest,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
) -> PlanDetailOut:
    """
    Mengubah seluruh isi SK (draf) dalam satu transaksi (PUT).
    Termasuk draf revisi setelah adendum diminta.
    
    Path Parameters:
    - plan_id (UUID): ID dari SK.
    
    Request Body:
    - data (PlanDraftRequest): Data draft SK yang lengkap.
    
    Returns:
    - PlanDetailOut: Detail lengkap SK yang baru disimpan.
    """
    # Memastikan hak akses level PM_UNIT dengan Dependency Injection
    # Menyampaikan update ke service layer
    return PlanDetailOut(**await plan_draft_service.edit_draft(access.user, plan_id, data))


@router.get("/{plan_id}/preview", response_class=HTMLResponse)
async def preview_plan(
    plan_id: UUID,
    access: PlanAccess = _VIEW_ACCESS,
    plan_draft_service: PlanDraftService = Depends(get_plan_draft_service),
) -> HTMLResponse:
    """
    Pratinjau A4 draf SK ("Sunting SK", SK2-C) — format sama dengan dokumen terbit (GET).
    
    Path Parameters:
    - plan_id (UUID): ID dari SK.
    
    Returns:
    - HTMLResponse: Representasi HTML draf SK.
    """
    # Menggunakan Dependency Injection untuk hak akses baca dan PlanDraftService
    # Memanggil service detail untuk di-render menjadi HTML pratinjau
    return HTMLResponse(render_plan_preview_html(await plan_draft_service.detail(plan_id)))

@router.post("", response_model=WorkPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: WorkPlanCreate,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PLAN)),
    db: AsyncSession = Depends(get_db_with_user),
    plan_assignment_service: PlanAssignmentService = Depends(get_plan_assignment_service)
) -> WorkPlanResponse:
    """
    Membuat draf rencana kerja (SK) baru (POST).
    
    Request Body:
    - data (WorkPlanCreate): Data awal pembuatan SK (unit, lokasi, ketua, dll).
    
    Returns:
    - WorkPlanResponse: Data rencana kerja yang baru dibuat.
    """
    # Menggunakan Dependency Injection (require_permission) untuk membatasi aksi ini
    # Inject database session (get_db_with_user)
    await check_unit_manager(db, data.unit_id, current_user)
    await ensure_same_org(db, current_user.organization_id, sites=[data.site_id],
                          employees=[data.pm_employee_id, data.leader_employee_id])
    assignments = plan_assignment_service
    # Memanggil service layer validasi plan_assignment
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
    """
    Mengubah rincian SK berstatus Draf (PATCH). (EDIT_DRAFT, dok 05)
    
    Path Parameters:
    - plan_id (UUID): ID dari rencana kerja (SK).
    
    Request Body:
    - data (WorkPlanUpdate): Data yang ingin diubah (judul, lokasi, dsb).
    
    Returns:
    - WorkPlanResponse: Data rencana kerja yang telah di-update.
    """
    # Menggunakan Dependency Injection untuk memastikan hak akses (_PM_UNIT_ACCESS) dan db session
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
    """
    Menambahkan data hari ke dalam rencana kerja berstatus DRAFT (POST).
    
    Path Parameters:
    - plan_id (UUID): ID rencana kerja.
    
    Request Body:
    - data (PlanDayCreate): Rincian hari yang akan ditambahkan.
    
    Returns:
    - PlanDayResponse: Data hari yang berhasil ditambahkan.
    """
    # Menggunakan Dependency Injection untuk hak akses _PM_UNIT_ACCESS dan sesi database (get_db_with_user)
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
    """
    Menambahkan tugas baru pada hari tertentu di dalam SK (POST).
    
    Path Parameters:
    - plan_id (UUID): ID rencana kerja (SK).
    - day_id (UUID): ID dari hari bersangkutan.
    
    Request Body:
    - data (PlanTaskCreate): Rincian tugas yang akan ditambahkan.
    
    Returns:
    - PlanTaskResponse: Data tugas yang berhasil dibuat.
    """
    # Menggunakan Dependency Injection untuk kontrol izin pada hari bersangkutan (_DAY_PM_UNIT_ACCESS)
    # Inject database session (get_db_with_user)
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
    """
    Menyusun ulang judul & tugas satu hari selagi SK masih draf (PUT).
    domain.js SAVE_DAY (V-23).
    
    Path Parameters:
    - plan_id (UUID): ID SK.
    - day_id (UUID): ID hari.
    
    Request Body:
    - data (DayPlanRequest): Data tugas untuk hari tersebut.
    
    Returns:
    - dict[str, object]: Data hari dan daftar tugas yang baru disimpan.
    """
    # Dependency Injection untuk akses tingkat hari (_DAY_PM_UNIT_ACCESS) dan db
    # Validasi di layer Service access untuk memastikan SK status DRAFT
    require_plan_status(access, PlanStatus.DRAFT)
    if not 1 <= len(data.tasks) <= 30:
        raise ValidationError("Isi antara 1 sampai 30 tugas per hari.")
    titles = [t.title.strip() for t in data.tasks]
    if not data.title.strip() or not all(titles):
        raise ValidationError("Judul hari dan setiap tugas wajib diisi.")
    await db.execute(text("UPDATE vms.work_plan_day SET title = :title WHERE id = :day"),
                     {"title": data.title.strip(), "day": day_id})
    await db.execute(text("DELETE FROM vms.work_plan_task WHERE work_plan_day_id = :day"), {"day": day_id})
    if titles:
        ins = text("""
            INSERT INTO vms.work_plan_task (work_plan_day_id, title, sort_order)
            SELECT :day, u.title, u.sort
            FROM unnest(CAST(:titles AS text[]), CAST(:sorts AS int[])) AS u(title, sort)
        """)
        await db.execute(ins, {"day": day_id, "titles": titles, "sorts": list(range(len(titles)))})
    return {"id": str(day_id), "title": data.title.strip(), "tasks": titles}
