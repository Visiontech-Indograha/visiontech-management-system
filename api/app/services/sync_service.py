"""
app/services/sync_service.py
Sinkronisasi luring (M12; dok 02 A-08, dok 04 §7). Tiap operasi dijalankan dalam SAVEPOINT memakai
logika yang sama dengan jalur daring, lalu ditandai APPLIED / REJECTED (alasan disimpan, tidak dibuang).
Hanya aksi lapangan yang boleh luring; absensi, penerbitan & persetujuan wajib daring (waktu & geofence server).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, PlanAccess, PlanNeed, check_plan_access, ensure_same_org
from app.api.v1.endpoints import hse
from app.core.errors import AppError, NotFoundError
from app.crud.crud_plan_access import CRUDPlanAccess
from app.crud.crud_sync import CRUDSync
from app.schemas.hse import DailyReportCreate, IncidentCreate
from app.services.overtime_service import OvertimeService

OFFLINE_ALLOWED = ("DAILY_REPORT_SAVE", "DAILY_REPORT_SUBMIT", "TASK_TOGGLE", "INCIDENT_REPORT", "OVERTIME_REPORT")
NOT_OFFLINE = "Aksi ini tidak dapat dikirim saat luring."
INVALID = "Data operasi tidak valid."


def _message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    if isinstance(exc, HTTPException):
        detail = exc.detail
        return str(detail.get("message") if isinstance(detail, dict) else detail)
    return INVALID


class SyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDSync(db)

    async def _day_access(self, user: CurrentUser, plan_id: UUID, day_id: UUID) -> PlanAccess:
        access = await check_plan_access(self.db, plan_id, user, PlanNeed.LEADER)
        if str(await CRUDPlanAccess(self.db).plan_of_day(day_id)) != str(plan_id):
            raise NotFoundError("Hari kerja")
        return access

    async def _apply(self, user: CurrentUser, op_type: str, p: dict[str, Any]) -> None:
        if op_type in ("DAILY_REPORT_SAVE", "DAILY_REPORT_SUBMIT", "TASK_TOGGLE"):
            plan_id, day_id = UUID(str(p["plan_id"])), UUID(str(p["day_id"]))
            access = await self._day_access(user, plan_id, day_id)
            if op_type == "DAILY_REPORT_SAVE":
                data = DailyReportCreate(body=p["body"], obstacle=p["obstacle"],
                                         evidence_file_ids=p.get("evidence_file_ids", []))
                await hse.upsert_daily_report(day_id, data, access=access, db=self.db)
            elif op_type == "DAILY_REPORT_SUBMIT":
                await hse.submit_daily_report(day_id, access=access, db=self.db)
            else:
                await hse.toggle_task(day_id, UUID(str(p["task_id"])), access=access, db=self.db)
        elif op_type == "INCIDENT_REPORT":
            await hse.report_incident(IncidentCreate(**p), current_user=user, db=self.db)
        elif op_type == "OVERTIME_REPORT":
            plan_id = UUID(str(p["work_plan_id"]))
            await ensure_same_org(self.db, user.organization_id, work_plans=[plan_id])
            await OvertimeService(self.db).report(user, plan_id, float(p["hours"]), str(p["reason"]))

    async def apply_operations(self, user: CurrentUser, device_id: str,
                               operations: list[Any]) -> list[dict[str, Any]]:
        results = []
        for op in operations:
            row = await self.repo.enqueue(user.organization_id, user.user_id, device_id, op.client_op_id,
                                          op.op_type, op.payload, op.client_created_at)
            status, error = row.status, row.error_message
            if status == "PENDING":                       # belum pernah diproses → jalankan sekali
                if op.op_type not in OFFLINE_ALLOWED:
                    status, error = "REJECTED", NOT_OFFLINE
                else:
                    try:
                        async with self.db.begin_nested():
                            await self._apply(user, op.op_type, op.payload)
                        status, error = "APPLIED", None
                    except (AppError, HTTPException, PydanticValidationError, KeyError, ValueError,
                            TypeError) as exc:
                        status, error = "REJECTED", _message(exc)
                await self.repo.mark(row.id, status, error)
            results.append({"client_op_id": str(op.client_op_id), "status": status, "error_message": error})
        return results

    async def status(self, user: CurrentUser, since: datetime | None) -> list[Any]:
        return await self.repo.status_since(user.user_id, since)
