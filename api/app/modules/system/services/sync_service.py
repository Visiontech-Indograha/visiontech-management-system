"""
app/modules/system/services/sync_service.py
Sinkronisasi offline (M12; dok 02 A-08, dok 04 §7). Tiap operasi dijalankan dalam SAVEPOINT memakai
logika yang sama dengan jalur online, lalu ditandai APPLIED / REJECTED (alasan disimpan, tidak dibuang).
Hanya aksi lapangan yang boleh offline; absensi, penerbitan & persetujuan wajib online (waktu & geofence server).
Daily-first (Milestone 5): laporan harian jadwal dan lembur dapat diantrekan dari lapangan; laporan insiden SK V1
dipensiunkan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser
from app.modules.overtime.services.overtime_service import OvertimeService
from app.modules.system.repositories.sync_repository import CRUDSync
from app.modules.work_orders.schemas.work_order_schema import SurveySubmitIn
from app.modules.work_orders.services.work_order_service import WorkOrderService
from app.modules.work_plans.schemas.daily_report_schema import DailyReportCreate
from app.modules.work_plans.schemas.plan_item_schema import ProgressIn, RolloverRequest
from app.modules.work_plans.services.daily_plan_service import DailyPlanService
from app.modules.work_plans.services.plan_item_service import PlanItemService

OFFLINE_ALLOWED = (
    "OVERTIME_REPORT", "DAILY_REPORT_SUBMIT", "PLAN_ITEM_PROGRESS", "PLAN_ROLLOVER_REQUEST", "WO_SURVEY_SUBMIT",
)
NOT_OFFLINE = "Aksi ini tidak dapat dikirim saat offline."
INVALID = "Data operasi tidak valid."


def _message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    if isinstance(exc, HTTPException):
        detail = exc.detail
        return str(detail.get("message") if isinstance(detail, dict) else detail)
    return INVALID


class SyncService:
    """
    Layanan sinkronisasi untuk memproses antrean operasi yang dikirim oleh klien secara offline.
    Menjamin operasi divalidasi dengan aturan yang sama seperti saat online dan hasil sinkronisasi dicatat.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Inisialisasi SyncService.

        Args:
            db (AsyncSession): Sesi database asinkron.
        """
        self.db = db
        self.repo = CRUDSync(db)

    async def _apply(self, user: CurrentUser, op_type: str, p: dict[str, Any]) -> None:
        """
        Menerapkan satu buah operasi (payload) ke dalam sistem dengan menggunakan fungsi yang sama
        seperti endpoint online.

        Args:
            user (CurrentUser): Pengguna yang mengirimkan operasi.
            op_type (str): Tipe operasi (mis. DAILY_REPORT_SAVE).
            p (dict[str, Any]): Payload / data dari operasi.
        """
        if op_type == "OVERTIME_REPORT":
            daily_plan_id = UUID(str(p["daily_plan_id"]))
            await OvertimeService(self.db).report(user, daily_plan_id, float(p["hours"]), str(p["reason"]))
        elif op_type == "DAILY_REPORT_SUBMIT":
            daily_plan_id = UUID(str(p["daily_plan_id"]))
            report = DailyReportCreate(
                summary=str(p["summary"]),
                obstacles=p.get("obstacles"),
                photos_json=p.get("photos_json", []),
            )
            service = DailyPlanService(self.db)
            await service.submit_daily_report(user, daily_plan_id, report)
        elif op_type == "PLAN_ITEM_PROGRESS":
            # Foto yang sudah terunggah (`photos`) + foto baru yang diunggah HP saat sinkron: id berkas datang di
            # `evidence_file_ids` berurutan dengan `new_photo_requirements` (slot foto tiap berkas).
            photos = list(p.get("photos") or [])
            new_files = p.get("evidence_file_ids") or []
            new_slots = p.get("new_photo_requirements") or []
            photos += [{"file_id": f, "requirement_id": r} for f, r in zip(new_files, new_slots, strict=False)]
            data = ProgressIn(
                completed_qty=p["completed_qty"], photos=photos, notes=p.get("notes"),
            )
            await PlanItemService(self.db).progress(user, UUID(str(p["item_id"])), data)
        elif op_type == "PLAN_ROLLOVER_REQUEST":
            # Permintaan pindah hari dari HP (ketua): aturan & status sama dengan endpoint request-rollover.
            rollover = RolloverRequest(delay_reason=str(p["delay_reason"]), completed_qty=p["completed_qty"])
            await PlanItemService(self.db).request_rollover(user, UUID(str(p["item_id"])), rollover)
        elif op_type == "WO_SURVEY_SUBMIT":
            # Survei WO dari HP (tim): validasi & cakupan sama dengan POST /work-orders/{id}/submit-survey.
            # Foto titik: `photos` (sudah terunggah) + `evidence_file_ids` (berkas dari antrean foto HP) per titik.
            body = dict(p.get("survey") or {})
            points = []
            for pt in body.get("points") or []:
                pt = dict(pt)
                extra = pt.pop("evidence_file_ids", None) or []
                pt["photos"] = list(pt.get("photos") or []) + [{"file_id": str(f)} for f in extra]
                points.append(pt)
            body["points"] = points
            await WorkOrderService(self.db).submit_survey_offline(
                UUID(str(p["work_order_id"])), SurveySubmitIn.model_validate(body), user
            )

    async def apply_operations(self, user: CurrentUser, device_id: str, operations: list[Any]) -> list[dict[str, Any]]:
        """
        Memproses sekumpulan operasi dari antrean sinkronisasi offline yang dikirim klien.

        Args:
            user (CurrentUser): Pengguna pengirim.
            device_id (str): ID perangkat yang digunakan klien.
            operations (list[Any]): Daftar operasi yang akan disinkronisasi.

        Returns:
            list[dict[str, Any]]: Hasil proses tiap operasi (client_op_id, status, dan pesan galat jika ada).
        """
        results = []
        for op in operations:
            # Mendaftarkan operasi ke tabel sinkronisasi agar tidak terjadi double-processing
            row = await self.repo.enqueue(
                user.organization_id,
                user.user_id,
                device_id,
                op.client_op_id,
                op.op_type,
                op.payload,
                op.client_created_at,
            )
            status, error = row.status, row.error_message
            # Jika operasi belum pernah diproses (PENDING), maka eksekusi sekarang
            if status == "PENDING":
                if op.op_type not in OFFLINE_ALLOWED:
                    status, error = "REJECTED", NOT_OFFLINE
                else:
                    try:
                        # Jalankan aplikasi operasi di dalam nested transaction (SAVEPOINT)
                        # agar jika satu operasi gagal, operasi lainnya tetap bisa dilanjutkan.
                        async with self.db.begin_nested():
                            await self._apply(user, op.op_type, op.payload)
                        status, error = "APPLIED", None
                    except (AppError, HTTPException, PydanticValidationError, KeyError, ValueError, TypeError) as exc:
                        # Menangkap segala error validasi atau logika bisnis untuk ditandai sebagai ditolak
                        status, error = "REJECTED", _message(exc)
                # Menandai hasil akhir pemrosesan operasi di database
                await self.repo.mark(row.id, status, error)
            results.append({"client_op_id": str(op.client_op_id), "status": status, "error_message": error})
        return results

    async def status(self, user: CurrentUser, since: datetime | None) -> list[Any]:
        """
        Mengambil status operasi-operasi sinkronisasi yang pernah dikirimkan oleh pengguna.

        Args:
            user (CurrentUser): Pengguna.
            since (datetime | None): Filter waktu (mengembalikan operasi sejak waktu ini).

        Returns:
            list[Any]: Daftar status operasi.
        """
        return await self.repo.status_since(user.user_id, since)
