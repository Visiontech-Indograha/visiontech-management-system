"""
app/modules/attendance/controllers/attendance_controller.py

Controller orkestrasi use case absensi lapangan dan offline.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.permissions import Permission
from app.core.security import CurrentUser, create_time_anchor
from app.modules.attendance.dependencies import get_attendance_offline_service, get_attendance_session_service
from app.modules.attendance.schemas.attendance_schema import (
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    CheckOutRequest,
    DeviceKeyRequest,
    ExplanationRequest,
    MealAllowanceRow,
    OfflineAttendanceEvent,
    OfflineAttendanceResult,
    ReviewRequest,
)
from app.modules.attendance.services.attendance_service import (
    AttendanceOfflineService,
    AttendanceSessionService,
)


def _response(row: Any) -> AttendanceResponse:
    """Fungsi pembantu memetakan row hasil database menjadi AttendanceResponse."""
    return AttendanceResponse(**row._mapping)


class AttendanceController:
    """
    Controller use case absensi lapangan (check-in, check-out, review, ekspor, dan event offline).
    """

    def __init__(
        self,
        attendance_session_service: AttendanceSessionService = Depends(get_attendance_session_service),
        offline_service: AttendanceOfflineService = Depends(get_attendance_offline_service),
    ) -> None:
        self.session_service = attendance_session_service
        self.offline_service = offline_service

    async def handle_list_attendance(
        self,
        current_user: CurrentUser,
        employee_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        scope: str = "all",
        page: int = 1,
        size: int = 50,
    ) -> AttendanceListResponse:
        """Mengambil daftar riwayat absensi berdasarkan filter dan kewenangan pengguna."""
        rows, total = await self.session_service.list_attendance(
            current_user.organization_id,
            current_user.user_id,
            view_all=Permission.VIEW_ALL_ATTENDANCE.value in current_user.permissions,
            employee_id=employee_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            scope=scope,
            page=page,
            size=size,
        )
        today, required_out, pending, pending_plan = await self.session_service.day_hints(
            current_user.organization_id, current_user.employee_id
        )
        return AttendanceListResponse(
            items=[_response(r) for r in rows],
            total=total,
            page=page,
            size=size,
            today=today,
            required_out_at=required_out,
            report_pending_count=pending,
            report_pending_plan_id=pending_plan,
            time_anchor=create_time_anchor(current_user.user_id),
        )

    async def handle_register_device_key(
        self,
        current_user: CurrentUser,
        data: DeviceKeyRequest,
    ) -> dict[str, str]:
        """Mendaftarkan kunci publik Android Keystore perangkat untuk verifikasi absen offline."""
        await self.offline_service.register_device_key(current_user, data.device_id, data.public_key)
        return {"message": "Kunci perangkat terdaftar."}

    async def handle_submit_offline(
        self,
        current_user: CurrentUser,
        data: OfflineAttendanceEvent,
    ) -> OfflineAttendanceResult:
        """Memproses sinkronisasi event absen offline bertanda tangan kriptografis."""
        result = await self.offline_service.apply(
            current_user,
            device_id=data.device_id,
            client_op_id=data.client_op_id,
            kind=data.kind,
            payload=data.payload,
            signature=data.signature,
            selfie_file_id=data.selfie_file_id,
        )
        return OfflineAttendanceResult(**result)

    async def handle_check_in(
        self,
        current_user: CurrentUser,
        data: CheckInRequest,
    ) -> AttendanceResponse:
        """Memproses absensi masuk (check-in) pengguna."""
        await self.session_service.ensure_check_in_refs(current_user.organization_id, data.site_id, data.selfie_file_id)
        row = await self.session_service.check_in(
            current_user.organization_id,
            current_user.user_id,
            site_id=data.site_id,
            lng=data.location.lng,
            lat=data.location.lat,
            origin=data.location_origin,
            accuracy_m=data.accuracy_m,
            selfie_file_id=data.selfie_file_id,
            channel=data.channel,
            explanation=data.explanation,
        )
        return _response(row)

    async def handle_check_out(
        self,
        current_user: CurrentUser,
        data: CheckOutRequest,
    ) -> AttendanceResponse:
        """Memproses absensi pulang (check-out) pengguna."""
        await self.session_service.ensure_check_in_refs(current_user.organization_id, None, data.selfie_file_id)
        row = await self.session_service.check_out(
            current_user.user_id,
            data.channel,
            org_id=current_user.organization_id,
            lat=data.location.lat,
            lng=data.location.lng,
            selfie_file_id=data.selfie_file_id,
            explanation=data.explanation,
            accuracy_m=data.accuracy_m,
        )
        return _response(row)

    async def handle_explain(
        self,
        current_user: CurrentUser,
        att_id: UUID,
        data: ExplanationRequest,
    ) -> dict[str, str]:
        """Menambahkan catatan penjelasan atas absensi yang perlu review."""
        await self.session_service.explain_attendance(
            current_user.organization_id, current_user.user_id, att_id, data.explanation
        )
        return {"message": "Penjelasan ditambahkan."}

    async def handle_review(
        self,
        current_user: CurrentUser,
        att_id: UUID,
        data: ReviewRequest,
    ) -> dict[str, str]:
        """Meninjau dan memberikan keputusan persetujuan atas absensi bawahan."""
        status = await self.session_service.review_attendance(
            current_user.organization_id, current_user.user_id, att_id, data.is_approved, data.note
        )
        return {"message": f"Absensi di-{status.lower()}."}

    async def handle_export(
        self,
        current_user: CurrentUser,
        start_date: date,
        end_date: date,
    ) -> str:
        """Mengekspor data absensi organisasi dalam rentang tanggal ke format CSV."""
        return await self.session_service.export_csv(current_user.organization_id, start_date, end_date)

    async def handle_meal_allowance(
        self, current_user: CurrentUser, start_date: date, end_date: date, division_id: UUID | None
    ) -> list[MealAllowanceRow]:
        rows = await self.session_service.meal_allowance(current_user, start_date, end_date, division_id)
        return [MealAllowanceRow(**dict(r._mapping)) for r in rows]


__all__ = ["AttendanceController"]
