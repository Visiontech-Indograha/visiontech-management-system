from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse

from app.api.deps import (
    get_current_user,
    get_plan_assignment_service,
    get_plan_draft_service,
    get_plan_edit_service,
    get_plan_transition_service,
    plan_access,
    plan_day_access,
    require_permission,
)
from app.core.permissions import Permission
from app.core.security import CurrentUser
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
)
from app.services.pdf_service import render_plan_preview_html
from app.services.plan_assignment_service import PlanAssignmentService
from app.services.plan_draft_service import PlanDraftService
from app.services.plan_edit_service import PlanEditService
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
    plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
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
    await plan_transition_service.start_due_plans(current_user.organization_id)
    rows = await plan_edit_service.visible_plans(current_user, status_filter, archived)
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
    return PlanDetailOut(**await plan_draft_service.detail(plan_id, include_drafts=access.is_leader))


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
    plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
) -> WorkPlanResponse:
    """
    Membuat draf rencana kerja (SK) baru (POST).

    Request Body:
    - data (WorkPlanCreate): Data awal pembuatan SK (unit, lokasi, ketua, dll).

    Returns:
    - WorkPlanResponse: Data rencana kerja yang baru dibuat.
    """
    row = await plan_edit_service.create(current_user, data)
    return WorkPlanResponse(
        **data.model_dump(),
        id=row.id, number=row.number, status=row.status,
        revision=row.revision, row_version=row.row_version,
        cancellation_reason=row.cancellation_reason
    )


@router.patch("/{plan_id}", response_model=WorkPlanResponse)  # EDIT_DRAFT (dok 05)
async def update_plan(
    plan_id: UUID,
    data: WorkPlanUpdate,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
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
    updated = await plan_edit_service.update(access, plan_id, data)
    return WorkPlanResponse(**updated._mapping)


@router.post("/{plan_id}/days", response_model=PlanDayResponse)
async def add_day(
    plan_id: UUID,
    data: PlanDayCreate,
    access: PlanAccess = _PM_UNIT_ACCESS,
    plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
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
    day_id = await plan_edit_service.add_day(access, plan_id, data.work_date, data.title, data.sort_order)
    return PlanDayResponse(id=day_id, work_plan_id=plan_id, **data.model_dump())


@router.post("/{plan_id}/days/{day_id}/tasks", response_model=PlanTaskResponse)
async def add_task(
    plan_id: UUID,
    day_id: UUID,
    data: PlanTaskCreate,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
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
    task_id = await plan_edit_service.add_task(day_id, data.title, data.sort_order)
    return PlanTaskResponse(id=task_id, work_plan_day_id=day_id, is_done=False, **data.model_dump())


@router.put("/{plan_id}/days/{day_id}/plan")
async def save_day(
    plan_id: UUID,
    day_id: UUID,
    data: DayPlanRequest,
    access: PlanAccess = _DAY_PM_UNIT_ACCESS,
    plan_edit_service: PlanEditService = Depends(get_plan_edit_service),
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
    title, tasks = await plan_edit_service.save_day(access, day_id, data.title, [t.title for t in data.tasks])
    return {"id": str(day_id), "title": title, "tasks": tasks}
