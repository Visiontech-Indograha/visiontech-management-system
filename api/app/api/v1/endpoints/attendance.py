"""
Absensi lapangan. Tipis (dok 12 §2): aturan di services/attendance_session_service.py (V-12),
SQL di crud/crud_attendance_session.py; jarak/status/terlambat/pulang cepat diputuskan trigger.
"""
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.api.deps import (
    get_attendance_offline_service,
    get_attendance_session_service,
    get_current_user,
    require_permission,
)
from app.core.permissions import Permission
from app.core.security import CurrentUser, create_time_anchor
from app.schemas.attendance import (
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    DeviceKeyRequest,
    ExplanationRequest,
    OfflineAttendanceEvent,
    OfflineAttendanceResult,
    ReviewRequest,
)
from app.services.attendance_offline_service import AttendanceOfflineService
from app.services.attendance_session_service import AttendanceSessionService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _response(row: Any) -> AttendanceResponse:
    """
    Fungsi pembantu untuk memetakan row hasil query menjadi skema AttendanceResponse.

    Args:
        row (Any): Row data dari database.

    Returns:
        AttendanceResponse: Skema respons absensi.
    """
    return AttendanceResponse(**row._mapping)


@router.get("", response_model=AttendanceListResponse)
async def list_attendance(
    employee_id: UUID | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    status: str | None = None,
    scope: str = Query("all", pattern="^(all|mine|team)$"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service)
) -> AttendanceListResponse:
    """
    Dok 05 §3.5 · R-33: Finance & OPS seluruh organisasi; PM miliknya + bawahan lapangan di unitnya;
    lainnya hanya milik sendiri. Filter `plan_id` di dok 05 belum didukung (dok 10 Bagian C).

    Query params:
    - employee_id: Filter UUID karyawan
    - from/to: Filter rentang tanggal
    - status: Filter status absensi
    - scope: `all` (bawaan), `mine` = absensi pribadi, `team` = absensi anggota/umum (selain milik sendiri)
    - page, size: Pagination

    Return: Daftar absensi (AttendanceListResponse)
    """
    # Mengambil objek AttendanceSessionService dari injeksi dependensi
    # Melakukan query list absensi melalui service dengan pengecekan VIEW_ALL_ATTENDANCE
    service = attendance_session_service
    rows, total = await service.list_attendance(
        current_user.organization_id, current_user.user_id,
        view_all=Permission.VIEW_ALL_ATTENDANCE.value in current_user.permissions,
        employee_id=employee_id, date_from=date_from, date_to=date_to, status=status, scope=scope,
        page=page, size=size)
    return AttendanceListResponse(items=[_response(r) for r in rows], total=total, page=page, size=size,
                                  today=await service.today(current_user.organization_id),
                                  time_anchor=create_time_anchor(current_user.user_id))


@router.post("/device-key")
async def register_device_key(
    data: DeviceKeyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    offline_service: AttendanceOfflineService = Depends(get_attendance_offline_service),
) -> dict[str, str]:
    """
    R-34: daftarkan kunci publik Android Keystore perangkat ini untuk memverifikasi absen luring.

    Body params:
    - data: Payload device id dan public key (DeviceKeyRequest)

    Return: Pesan sukses
    """
    # Injeksi AttendanceOfflineService untuk mengelola kunci offline perangkat
    await offline_service.register_device_key(current_user, data.device_id, data.public_key)
    return {"message": "Kunci perangkat terdaftar."}


@router.post("/offline", response_model=OfflineAttendanceResult)
async def submit_offline_attendance(
    data: OfflineAttendanceEvent,
    current_user: CurrentUser = Depends(get_current_user),
    offline_service: AttendanceOfflineService = Depends(get_attendance_offline_service),
) -> OfflineAttendanceResult:
    """
    R-34: terima satu absen luring yang ditandatangani perangkat (idempoten per client_op_id).

    Body params:
    - data: Event absensi luring berserta signature (OfflineAttendanceEvent)

    Return: Hasil pemrosesan sinkronisasi offline (OfflineAttendanceResult)
    """
    # Menggunakan dependensi offline_service
    result = await offline_service.apply(
        current_user, device_id=data.device_id, client_op_id=data.client_op_id, kind=data.kind,
        payload=data.payload, signature=data.signature, selfie_file_id=data.selfie_file_id,
        face_probe_id=data.face_probe_id)
    return OfflineAttendanceResult(**result)


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    data: CheckInRequest,
    current_user: CurrentUser = Depends(get_current_user),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service)
) -> AttendanceResponse:
    """
    P4-2 · domain.js CHECK_IN. Waktu, tanggal, jarak, dan status dari server (aturan inti #3).
    Pekerja lapangan lewat HP (`channel` MOBILE), pekerja kantor lewat web (`channel` WEB).

    Body params:
    - data: Data check in termasuk lokasi dan bukti foto (CheckInRequest)

    Return: Detail absensi check in (AttendanceResponse)
    """
    # Mengambil sesi DB dari Depends (get_db_with_user) untuk pengecekan referensi yang aman
    # Serta dependensi attendance_session_service untuk menjalankan transaksi absensi
    await attendance_session_service.ensure_check_in_refs(current_user.organization_id, data.site_id,
                                                         data.selfie_file_id)
    row = await attendance_session_service.check_in(
        current_user.organization_id, current_user.user_id, site_id=data.site_id,
        lng=data.location.lng, lat=data.location.lat, origin=data.location_origin,
        accuracy_m=data.accuracy_m, selfie_file_id=data.selfie_file_id,
        channel=data.channel, explanation=data.explanation,
        face_probe_id=data.face_probe_id,
    )
    return _response(row)


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    data: CheckOutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service)
) -> AttendanceResponse:
    """
    domain.js CHECK_OUT — menutup sesi terbuka milik sendiri, dari kanal sesuai jenis pekerja.

    Body params:
    - data: Data check out dengan spesifikasi channel (CheckOutRequest)

    Return: Detail absensi setelah check out (AttendanceResponse)
    """
    # Menggunakan dependensi attendance_session_service
    await attendance_session_service.ensure_check_in_refs(current_user.organization_id, None, data.selfie_file_id)
    return _response(await attendance_session_service.check_out(
        current_user.user_id, data.channel, org_id=current_user.organization_id,
        face_probe_id=data.face_probe_id, lat=data.location.lat, lng=data.location.lng,
        selfie_file_id=data.selfie_file_id, explanation=data.explanation, accuracy_m=data.accuracy_m,
    ))


@router.post("/{att_id}/explain")
async def explain_attendance(
    att_id: UUID,
    data: ExplanationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service)
) -> dict[str, str]:
    """
    P4-4 · domain.js EXPLAIN_ATTENDANCE — hanya absensi sendiri yang menunggu pemeriksaan.

    Path params:
    - att_id: UUID absensi

    Body params:
    - data: Catatan penjelasan absensi (ExplanationRequest)

    Return: Pesan sukses
    """
    # Meneruskan fungsi anotasi/penjelasan (explain) ke attendance_session_service dari Depends
    await attendance_session_service.explain_attendance(current_user.organization_id, current_user.user_id, att_id, data.explanation)
    return {"message": "Penjelasan ditambahkan."}


@router.post("/{att_id}/review")
async def review_attendance(
    att_id: UUID,
    data: ReviewRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.REVIEW_ATTENDANCE)),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service)
) -> dict[str, str]:
    """
    P4-4 · domain.js REVIEW_ATTENDANCE · R-33: PM → bawahan lapangan, Finance → kantor non-Finance,
    OPS → Finance; tidak pernah absensi sendiri.

    Path params:
    - att_id: UUID absensi yang direview

    Body params:
    - data: Persetujuan atau penolakan dengan catatan (ReviewRequest)

    Return: Pesan hasil review
    """
    # Diwajibkan memiliki izin REVIEW_ATTENDANCE (via Depends)
    # Memanggil service layer untuk menetapkan status absensi
    status = await attendance_session_service.review_attendance(
        current_user.organization_id, current_user.user_id, att_id, data.is_approved, data.note)
    return {"message": f"Absensi di-{status.lower()}."}


@router.get("/export", response_class=PlainTextResponse)
async def export_attendance(
    start_date: date,
    end_date: date,
    current_user: CurrentUser = Depends(require_permission(Permission.EXPORT_ATTENDANCE)),
    attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service),
) -> str:
    """
    P4-5: Ekspor CSV untuk Finance. Jam dalam zona waktu organisasi (sebelumnya tercetak UTC).

    Query params:
    - start_date: Tanggal mulai ekspor
    - end_date: Tanggal akhir ekspor

    Return: Data mentah format CSV
    """
    return await attendance_session_service.export_csv(current_user.organization_id, start_date, end_date)
