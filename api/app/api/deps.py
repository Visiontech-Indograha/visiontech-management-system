"""
Modul dependensi (dependencies) FastAPI untuk VMS.

Berisi fungsi-fungsi dependency injection (DI) untuk mendapatkan sesi database,
pengguna saat ini (current user), otorisasi peran/akses, dan pembuatan service.
"""
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from typing import Any, Literal
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.alerts import send_security_alert
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.permissions import NO_GLOBAL_ROLE, Permission, permissions_for_roles
from app.core.security import CurrentUser, verify_jwt_token
from app.crud.crud_attendance_monitor import CRUDAttendanceMonitor
from app.crud.crud_attendance_offline import CRUDAttendanceOffline
from app.crud.crud_attendance_session import CRUDAttendanceSession
from app.crud.crud_audit import CRUDAudit
from app.crud.crud_document import CRUDDocument
from app.crud.crud_employee import CRUDEmployee
from app.crud.crud_face import CRUDFace
from app.crud.crud_file import CRUDFile
from app.crud.crud_org_clock import CRUDOrgClock
from app.crud.crud_plan_access import CRUDPlanAccess
from app.crud.crud_plan_assignment import CRUDPlanAssignment
from app.crud.crud_plan_member import CRUDPlanMember
from app.crud.crud_plan_transition import CRUDPlanTransition
from app.crud.crud_session import CRUDSession
from app.crud.crud_site import CRUDSite
from app.crud.crud_unit import CRUDUnit
from app.crud.crud_user import CRUDUser
from app.db.session import AsyncSessionLocal, set_request_context, unit_of_work
from app.services.access_service import PlanAccess, PlanNeed, check_plan_access
from app.services.account_service import AccountService
from app.services.app_release_service import AppReleaseService
from app.services.asset_reservation_service import AssetReservationService
from app.services.attendance_monitor_service import AttendanceMonitorService
from app.services.attendance_offline_service import AttendanceOfflineService
from app.services.attendance_session_service import AttendanceSessionService
from app.services.audit_service import AuditService
from app.services.auth_flow import AuthFlowService
from app.services.document_service import DocumentService
from app.services.employee_service import EmployeeService
from app.services.face_embed_client import FaceEmbedClient
from app.services.face_service import FaceService
from app.services.file_service import FileService
from app.services.hse_service import HseService
from app.services.member_report_service import MemberReportService
from app.services.monitoring_service import MonitoringService
from app.services.notification_service import NotificationService
from app.services.overtime_service import OvertimeService
from app.services.plan_amendment_service import PlanAmendmentService
from app.services.plan_assignment_service import PlanAssignmentService
from app.services.plan_attachment_service import PlanAttachmentService
from app.services.plan_change_service import PlanChangeService
from app.services.plan_day_service import PlanDayService
from app.services.plan_draft_service import PlanDraftService
from app.services.plan_edit_service import PlanEditService
from app.services.plan_location_service import PlanLocationService
from app.services.plan_member_service import PlanMemberService
from app.services.plan_revision_service import PlanRevisionService
from app.services.plan_transition_service import PlanTransitionService
from app.services.signature_service import SignatureService
from app.services.site_service import SiteService
from app.services.sync_service import SyncService
from app.services.unit_service import UnitService
from app.services.weekly_report_service import WeeklyReportService
from app.services.work_type_service import WorkTypeService

logger = logging.getLogger(__name__)
# Keamanan dengan skema Bearer token
security = HTTPBearer(auto_error=False)  # token hilang → 401 UNAUTHENTICATED kita sendiri

# "function": commit/rollback terjadi SEBELUM respons dikirim, jadi commit yang gagal
# sampai ke klien sebagai 500 — bukan 200 untuk data yang ternyata tidak tersimpan.
DB_SCOPE: Literal["function", "request"] = "function"


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Menyediakan sesi database asinkron (AsyncSession) untuk satu siklus permintaan.
    Satu permintaan = satu transaksi: commit bila handler sukses, rollback bila galat (T-02).
    """
    async with AsyncSessionLocal() as session, unit_of_work(session):
        yield session


def _unauthenticated() -> AppError:
    """Mengembalikan objek AppError standar untuk otentikasi gagal (401)."""
    return AppError("UNAUTHENTICATED", "Sesi berakhir. Silakan masuk kembali.", status=401)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
) -> CurrentUser:
    """
    Mendapatkan pengguna saat ini yang sedang login berdasarkan token JWT.
    Token hanya membawa identitas (`sub`, `org`, `jti`). Status akun dan peran dibaca dari
    basis data pada setiap permintaan (dok 05 §4): mencabut peran atau menonaktifkan akun
    berlaku pada permintaan berikutnya.
    """
    if credentials is None:
        raise _unauthenticated()
    try:
        payload = verify_jwt_token(credentials.credentials)
    except jwt.PyJWTError:
        raise _unauthenticated() from None

    user_id, session_id = payload.get("sub"), payload.get("jti")
    if not user_id or not session_id:
        raise _unauthenticated()

    # Memuat identitas dan peran terbaru dari database
    identity = await CRUDUser(db).find_identity(user_id)
    if not identity or not identity.is_active:
        raise _unauthenticated()

    roles = list(identity.roles)
    return CurrentUser(
        user_id=user_id,
        organization_id=str(identity.organization_id),
        email=identity.login,
        role=roles[0] if roles else NO_GLOBAL_ROLE,
        roles=roles,
        session_id=session_id,
        permissions=permissions_for_roles(roles or [NO_GLOBAL_ROLE]),
    )


def require_permission(
    required_permission: Permission,
) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    """
    Memastikan pengguna saat ini memiliki izin (Permission) tertentu.
    Jika tidak, akan memunculkan galat 403 Forbidden.
    """
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if required_permission.value not in current_user.permissions:
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


def require_any_permission(
    *required: Permission,
) -> Callable[[CurrentUser], Coroutine[Any, Any, CurrentUser]]:
    """Lolos bila pengguna punya SALAH SATU izin yang disebut (mis. cari alamat: pengelola SK atau pengelola lokasi)."""
    async def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(p.value in current_user.permissions for p in required):
            raise AppError("FORBIDDEN", "Anda tidak memiliki akses untuk tindakan ini.", status=403)
        return current_user
    return permission_checker


async def get_db_with_user(
    db: AsyncSession = Depends(get_db, scope=DB_SCOPE),
    current_user: CurrentUser = Depends(get_current_user),
) -> AsyncSession:
    """
    Menyediakan sesi database asinkron dengan konteks pengguna untuk RLS (Row-Level Security).
    Konteks mencakup ID pengguna, organisasi, dan email untuk keperluan audit.
    """
    # Konteks RLS & audit untuk transaksi permintaan ini (app/db/session.py).
    try:
        await set_request_context(
            db,
            user_id=current_user.user_id,
            organization_id=current_user.organization_id,
            actor_label=current_user.email,
        )
    except SQLAlchemyError as exc:
        # Dok 17: tanpa data pribadi & tanpa isi galat DB ke Discord; detail lengkap ada di log.
        logger.exception("Konteks RLS gagal disetel")
        await send_security_alert(
            "Konteks RLS Gagal Disetel", f"Gagal menetapkan konteks RLS ({type(exc).__name__})."
        )
        raise AppError("INTERNAL_ERROR", "Terjadi gangguan pada sistem. Coba lagi beberapa saat; bila berulang, hubungi admin.", status=500) from None
    return db


def plan_access(need: PlanNeed, archived: bool | None = False) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{plan_id}`. `archived=None`: SK aktif maupun draf terarsip
    (pemulihan) — terarsip tetap hanya terlihat oleh pengelola."""
    async def guard(
        plan_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        return await check_plan_access(db, plan_id, current_user, need, archived)
    return guard


def allocation_plan_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{alloc_id}` — kewenangan mengikuti SK peminjam aset."""
    async def guard(
        alloc_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        plan_id = await CRUDPlanAccess(db).plan_of_allocation(alloc_id)
        if plan_id is None:
            raise NotFoundError("Alokasi aset")
        return await check_plan_access(db, plan_id, current_user, need)
    return guard


def incident_plan_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute ber-`{inc_id}` — kewenangan mengikuti SK tempat insiden terjadi."""
    async def guard(
        inc_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        plan_id = await CRUDPlanAccess(db).plan_of_incident(inc_id, current_user.organization_id)
        if plan_id is None:
            raise NotFoundError("Insiden")
        return await check_plan_access(db, plan_id, current_user, need)
    return guard


def plan_day_access(need: PlanNeed) -> Callable[..., Awaitable[PlanAccess]]:
    """Dependency untuk rute `/work-plans/{plan_id}/days/{day_id}` (V-16, dok 05 §3.6): kewenangan
    atas SK, dan hari harus milik SK itu — hari SK lain → 404."""
    async def guard(
        plan_id: UUID,
        day_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_with_user),
    ) -> PlanAccess:
        access = await check_plan_access(db, plan_id, current_user, need)
        if str(await CRUDPlanAccess(db).plan_of_day(day_id)) != str(plan_id):
            raise NotFoundError("Hari kerja")
        return access
    return guard


# ── Perakitan service (R-28 M5) ─────────────────────────────────────────────
# Getter memakai dependency sesi yang SAMA dengan handler (`get_db_with_user`; `get_db` untuk rute publik;
# `get_db` + `DB_SCOPE` untuk auth), sehingga FastAPI memakai ulang satu sesi = satu transaksi per permintaan.


def get_account_service(db: AsyncSession = Depends(get_db_with_user)) -> AccountService:
    return AccountService(CRUDUser(db), CRUDEmployee(db), CRUDSession(db))


def get_audit_service(db: AsyncSession = Depends(get_db_with_user)) -> AuditService:
    return AuditService(CRUDAudit(db))


def get_asset_reservation_service(db: AsyncSession = Depends(get_db_with_user)) -> AssetReservationService:
    return AssetReservationService(db)


def get_attendance_monitor_service(db: AsyncSession = Depends(get_db_with_user)) -> AttendanceMonitorService:
    return AttendanceMonitorService(CRUDAttendanceMonitor(db))


def get_face_embed_client() -> FaceEmbedClient:
    """Klien face-service. Dependency tersendiri agar uji dapat menggantinya dengan tiruan."""
    return FaceEmbedClient()


def get_face_service(db: AsyncSession = Depends(get_db_with_user),
                     client: FaceEmbedClient = Depends(get_face_embed_client)) -> FaceService:
    return FaceService(CRUDFace(db), client)


def get_attendance_session_service(db: AsyncSession = Depends(get_db_with_user),
                                   client: FaceEmbedClient = Depends(get_face_embed_client)) -> AttendanceSessionService:
    return AttendanceSessionService(CRUDAttendanceSession(db), CRUDOrgClock(db), FaceService(CRUDFace(db), client))


def get_site_service(db: AsyncSession = Depends(get_db_with_user)) -> SiteService:
    return SiteService(CRUDSite(db))


def get_attendance_offline_service(db: AsyncSession = Depends(get_db_with_user),
                                   client: FaceEmbedClient = Depends(get_face_embed_client)) -> AttendanceOfflineService:
    faces = FaceService(CRUDFace(db), client)
    return AttendanceOfflineService(CRUDAttendanceOffline(db),
                                    AttendanceSessionService(CRUDAttendanceSession(db), CRUDOrgClock(db), faces))


def get_document_service(db: AsyncSession = Depends(get_db_with_user)) -> DocumentService:
    return DocumentService(CRUDDocument(db))


def get_employee_service(db: AsyncSession = Depends(get_db_with_user)) -> EmployeeService:
    return EmployeeService(db)


def get_file_service(db: AsyncSession = Depends(get_db_with_user)) -> FileService:
    return FileService(CRUDFile(db))


def get_hse_service(db: AsyncSession = Depends(get_db_with_user)) -> HseService:
    return HseService(db)


def get_monitoring_service(db: AsyncSession = Depends(get_db_with_user)) -> MonitoringService:
    return MonitoringService(db)


def get_overtime_service(db: AsyncSession = Depends(get_db_with_user)) -> OvertimeService:
    return OvertimeService(db)


def get_plan_assignment_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanAssignmentService:
    return PlanAssignmentService(CRUDPlanAssignment(db))


def get_plan_attachment_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanAttachmentService:
    return PlanAttachmentService(db)


def get_plan_change_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanChangeService:
    return PlanChangeService(db)


def get_plan_day_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanDayService:
    return PlanDayService(db)


def get_plan_amendment_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanAmendmentService:
    return PlanAmendmentService(db)


def get_work_type_service(db: AsyncSession = Depends(get_db_with_user)) -> WorkTypeService:
    return WorkTypeService(db)


def get_plan_revision_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanRevisionService:
    return PlanRevisionService(db)


def get_plan_draft_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanDraftService:
    return PlanDraftService(db)


def get_member_report_service(db: AsyncSession = Depends(get_db_with_user)) -> MemberReportService:
    return MemberReportService(db)


def get_notification_service(db: AsyncSession = Depends(get_db_with_user)) -> NotificationService:
    return NotificationService(db)


def get_plan_edit_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanEditService:
    return PlanEditService(db, PlanAssignmentService(CRUDPlanAssignment(db)))


def get_plan_location_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanLocationService:
    return PlanLocationService(db)


def get_plan_member_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanMemberService:
    return PlanMemberService(CRUDPlanMember(db))


def get_plan_transition_service(db: AsyncSession = Depends(get_db_with_user)) -> PlanTransitionService:
    return PlanTransitionService(CRUDPlanTransition(db), CRUDPlanMember(db))


def get_signature_service(db: AsyncSession = Depends(get_db_with_user)) -> SignatureService:
    return SignatureService(db)


def get_sync_service(db: AsyncSession = Depends(get_db_with_user)) -> SyncService:
    return SyncService(db)


def get_app_release_service() -> AppReleaseService:
    """Rilis APK dibaca dari folder berkas (publik, tanpa sesi DB) — docs/32."""
    return AppReleaseService(settings.APP_RELEASE_DIR)


def get_unit_service(db: AsyncSession = Depends(get_db_with_user)) -> UnitService:
    return UnitService(CRUDUnit(db))


def get_weekly_report_service(db: AsyncSession = Depends(get_db_with_user)) -> WeeklyReportService:
    return WeeklyReportService(db)


def get_public_signature_service(db: AsyncSession = Depends(get_db)) -> SignatureService:
    return SignatureService(db)


def get_auth_flow_service(db: AsyncSession = Depends(get_db, scope=DB_SCOPE)) -> AuthFlowService:
    return AuthFlowService(db)
