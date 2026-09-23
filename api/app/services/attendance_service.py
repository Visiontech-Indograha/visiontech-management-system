"""
app/services/attendance_service.py
Aturan bisnis absensi lapangan.
Server tidak mempercayai perangkat — waktu dan jarak dihitung ulang di sini.
"""
from __future__ import annotations

from uuid import UUID
from datetime import date, time as dtime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, InvalidStateError, NotFoundError
from app.core.time import utcnow, jakarta_now
from app.repositories.attendance_repo import AttendanceRepo

# Jam kerja standar dalam WIB (bisa dijadikan config per organisasi nantinya)
_WORK_START = dtime(8, 0)   # 08:00
_WORK_END   = dtime(17, 0)  # 17:00


class AttendanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AttendanceRepo(db)

    async def check_in(
        self,
        org_id: UUID,
        employee_id: UUID,
        site_id: UUID,
        lat: float,
        lng: float,
        location_origin: str,
        selfie_file_id: UUID | None,
        face_result: str | None,
        face_similarity: float | None,
    ) -> Any:
        """
        Proses check-in lapangan:
        1. Validasi site ada.
        2. Hitung jarak ke site (server-side via PostGIS).
        3. Cek apakah sudah check-in hari ini.
        4. Tentukan status: AUTO_VALID / NEEDS_REVIEW.
        5. Insert attendance.
        """
        site = await self.repo.get_site(site_id, org_id)
        if not site:
            raise NotFoundError("Lokasi proyek")

        # Hitung jarak dari koordinat klien ke lokasi site di server
        distance_m = await self.repo.distance_to_site(lat, lng, site.location)
        radius = site.radius_m

        now_jakarta = jakarta_now()
        work_date = now_jakarta.date()
        now_time   = now_jakarta.time()

        # Cek duplikat check-in
        existing = await self.repo.get_active_checkin(employee_id, work_date)
        if existing:
            raise AppError(
                "ALREADY_CHECKED_IN",
                "Anda sudah melakukan absensi masuk hari ini.",
                status=409,
            )

        # Tentukan status
        is_late  = now_time > _WORK_START
        status   = "AUTO_VALID"

        if distance_m > radius:
            status = "NEEDS_REVIEW"          # Di luar radius
        if location_origin not in ("GPS",):
            status = "NEEDS_REVIEW"          # GPS palsu / simulasi
        if face_result in ("NO_MATCH", "LOW_QUALITY"):
            status = "NEEDS_REVIEW"          # Wajah tidak cocok — bukan ditolak

        row = await self.repo.create_checkin({
            "org": org_id, "emp": employee_id, "wdate": work_date,
            "site": site_id, "slabel": site.name,
            "lat": lat, "lng": lng,
            "orig": location_origin, "dist": distance_m, "rad": radius,
            "late": is_late, "file": selfie_file_id, "status": status,
            "f_res": face_result, "f_sim": face_similarity,
        })
        return row

    async def check_out(
        self,
        org_id: UUID,
        employee_id: UUID,
    ) -> Any:
        now_jakarta = jakarta_now()
        work_date   = now_jakarta.date()
        now_time    = now_jakarta.time()

        record = await self.repo.get_active_checkin(employee_id, work_date)
        if not record:
            raise AppError(
                "NO_ACTIVE_CHECKIN",
                "Tidak ada absensi masuk aktif yang ditemukan untuk hari ini.",
                status=404,
            )

        is_early_leave = now_time < _WORK_END
        # Pertahankan NEEDS_REVIEW jika sudah dari check-in
        new_status = record.status if record.status == "NEEDS_REVIEW" else "AUTO_VALID"

        return await self.repo.update_checkout(record.id, is_early_leave, new_status)
