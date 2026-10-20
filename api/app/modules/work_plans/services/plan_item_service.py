"""
app/modules/work_plans/services/plan_item_service.py
Layanan logika bisnis untuk tugas harian (work_plan_item).
Menangani deteksi tabrakan waktu, pelaporan capaian progres,
pengajuan rollover, dan tindakan PM Full Override.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser
from app.modules.work_plans.repositories.plan_item_repository import CRUDPlanItem
from app.modules.work_plans.schemas.plan_item_schema import (
    CheckConflictIn,
    CheckConflictOut,
    ConflictDetailOut,
    GenerateCompletionOut,
    PmApproveOrMoveIn,
    PmApproveOrMoveOut,
    RequestRolloverIn,
    RequestRolloverOut,
    TaskChainItemDetailOut,
    TaskChainStatusOut,
    UpdateItemProgressIn,
    UpdateItemProgressOut,
)


class PlanItemService:
    """Layanan orkestrasi item tugas harian."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CRUDPlanItem(db)

    async def check_conflicts(self, data: CheckConflictIn) -> CheckConflictOut:
        """Memeriksa potensi tabrakan jam penugasan antar teknisi atau kendaraan."""
        conflicts: list[ConflictDetailOut] = []

        # 1. Periksa tabrakan jadwal teknisi
        if data.employee_ids:
            emp_rows = await self.repo.check_employee_conflicts(
                work_date=data.work_date,
                start_time=data.start_time,
                end_time=data.end_time,
                employee_ids=data.employee_ids,
                exclude_item_id=data.exclude_item_id,
            )
            for r in emp_rows:
                conflicts.append(
                    ConflictDetailOut(
                        conflict_type="EMPLOYEE",
                        entity_id=r.employee_id,
                        entity_name=r.full_name,
                        conflicting_item_id=r.item_id,
                        conflicting_title=r.title,
                        start_time=r.start_time,
                        end_time=r.end_time,
                    )
                )

        # 2. Periksa tabrakan jadwal kendaraan
        if data.vehicle_id:
            veh_rows = await self.repo.check_vehicle_conflicts(
                work_date=data.work_date,
                start_time=data.start_time,
                end_time=data.end_time,
                vehicle_id=data.vehicle_id,
                exclude_item_id=data.exclude_item_id,
            )
            for r in veh_rows:
                conflicts.append(
                    ConflictDetailOut(
                        conflict_type="VEHICLE",
                        entity_id=r.vehicle_id,
                        entity_name=f"Armada {r.plate_number}",
                        conflicting_item_id=r.item_id,
                        conflicting_title=r.title,
                        start_time=r.start_time,
                        end_time=r.end_time,
                    )
                )

        return CheckConflictOut(has_conflict=len(conflicts) > 0, conflicts=conflicts)

    async def update_progress(self, item_id: UUID, data: UpdateItemProgressIn) -> UpdateItemProgressOut:
        """Memperbarui capaian aktual dan persentase progres tugas."""
        is_advancing = (
            (data.completed_qty is not None and data.completed_qty > 0)
            or (data.progress_percent is not None and data.progress_percent > 0)
            or (data.status is not None and data.status in ("IN_PROGRESS", "DONE"))
        )
        if is_advancing:
            parent_id, parent_title, parent_status = await self.repo.get_item_prerequisite(item_id)
            if parent_id and parent_status not in ("DONE", "COMPLETED"):
                raise AppError(
                    "PREREQUISITE_NOT_MET",
                    f"Tugas ini memiliki prasyarat '{parent_title}' yang belum selesai (status: {parent_status}). "
                    "Selesaikan tahapan prasyarat terlebih dahulu sebelum memulai atau mengisi progres.",
                    status=400,
                )

        row = await self.repo.update_progress(
            item_id=item_id,
            completed_qty=data.completed_qty,
            progress_percent=data.progress_percent,
            status=data.status,
            delay_reason=data.delay_reason,
        )
        if not row:
            raise AppError("NOT_FOUND", "Item rencana kerja tidak ditemukan.", status=404)

        return UpdateItemProgressOut(
            item_id=row.item_id,
            completed_qty=float(row.completed_qty or 0.0),
            progress_percent=float(row.progress_percent or 0.0),
            status=str(row.status),
            delay_reason=row.delay_reason,
        )

    async def request_rollover(self, item_id: UUID, data: RequestRolloverIn) -> RequestRolloverOut:
        """Mengajukan rollover tugas yang belum rampung ke hari berikutnya."""
        row = await self.repo.request_rollover(
            item_id=item_id,
            delay_reason=data.delay_reason,
            target_daily_plan_id=data.target_daily_plan_id,
        )
        if not row:
            raise AppError("NOT_FOUND", "Item rencana kerja tidak ditemukan.", status=404)

        return RequestRolloverOut(
            item_id=row.item_id,
            status=str(row.status),
            rollover_approval_status=str(row.rollover_approval_status),
            delay_reason=str(row.delay_reason),
            shifted_to_daily_id=row.shifted_to_daily_id,
        )

    async def pm_override_or_approve(
        self,
        current_user: CurrentUser,
        item_id: UUID,
        data: PmApproveOrMoveIn,
    ) -> PmApproveOrMoveOut:
        """Eksekusi kewenangan penuh PM (PM Full Override) untuk memindahkan tugas atau menyetujui rollover."""
        if not current_user.employee_id:
            raise AppError("FORBIDDEN", "Akun pengguna tidak memiliki data employee_id yang valid.", status=403)
        pm_employee_id = UUID(str(current_user.employee_id))

        action = data.action.upper()

        if action == "APPROVED":
            if not data.target_daily_plan_id:
                raise AppError("BAD_REQUEST", "Hari tujuan pemindahan tugas wajib ditentukan.", status=400)
            res = await self.repo.approve_rollover(
                item_id=item_id,
                pm_employee_id=pm_employee_id,
                pm_override_reason=data.pm_override_reason,
                target_daily_plan_id=data.target_daily_plan_id,
            )
            if not res:
                raise AppError("NOT_FOUND", "Item rencana kerja tidak ditemukan.", status=404)

            is_cross = res.get("is_cross_week", False)
            return PmApproveOrMoveOut(
                success=True,
                action="APPROVED",
                item_id=item_id,
                new_item_id=res["new_item_id"],
                status=res.get("status", "SHIFTED_DAY"),
                rollover_approval_status="APPROVED_BY_PM",
                message=(
                    "Rollover tugas berhasil disetujui (dialokasikan ke minggu berikutnya)."
                    if is_cross
                    else "Rollover tugas berhasil disetujui (digeser ke hari lain)."
                ),
            )

        elif action == "REJECTED":
            res = await self.repo.reject_rollover(
                item_id=item_id,
                pm_employee_id=pm_employee_id,
                pm_override_reason=data.pm_override_reason,
            )
            if not res:
                raise AppError("NOT_FOUND", "Item rencana kerja tidak ditemukan.", status=404)

            return PmApproveOrMoveOut(
                success=True,
                action="REJECTED",
                item_id=item_id,
                new_item_id=None,
                status="TODO",
                rollover_approval_status="REJECTED_BY_PM",
                message="Pengajuan rollover tugas ditolak oleh PM.",
            )

        elif action == "MOVE_SLOT":
            res = await self.repo.move_slot(
                item_id=item_id,
                pm_employee_id=pm_employee_id,
                pm_override_reason=data.pm_override_reason,
                target_daily_plan_id=data.target_daily_plan_id,
                target_start_time=data.target_start_time,
                target_end_time=data.target_end_time,
                new_status=data.new_status,
            )
            if not res:
                raise AppError("NOT_FOUND", "Item rencana kerja tidak ditemukan.", status=404)

            return PmApproveOrMoveOut(
                success=True,
                action="MOVE_SLOT",
                item_id=item_id,
                new_item_id=None,
                status=str(res.status),
                rollover_approval_status=str(res.rollover_approval_status),
                message="Slot item tugas berhasil dipindahkan secara langsung oleh PM.",
            )

        else:
            msg = f"Aksi '{data.action}' tidak valid. Pilihan: APPROVED, REJECTED, MOVE_SLOT"
            raise AppError("BAD_REQUEST", msg, status=400)

    async def get_task_chain_status(self, item_id: UUID) -> TaskChainStatusOut:
        """Mengambil data rantai tugas dari induk sampai cucu dan status kelayakan Work Completion."""
        data = await self.repo.get_task_chain_status(item_id)
        if not data:
            raise AppError("NOT_FOUND", "Item rencana kerja tidak ditemukan.", status=404)

        return TaskChainStatusOut(
            root_item_id=data["root_item_id"],
            initial_total_target=data["initial_total_target"],
            total_completed_across_weeks=data["total_completed_across_weeks"],
            total_progress_percent=data["total_progress_percent"],
            is_eligible_for_completion=data["is_eligible_for_completion"],
            status_label=data["status_label"],
            existing_completion_id=data["existing_completion_id"],
            all_linked_item_ids=data["all_linked_item_ids"],
            items=[TaskChainItemDetailOut(**it) for it in data["items"]],
        )

    async def generate_completion_from_chain(
        self,
        item_id: UUID,
        current_user: CurrentUser,
        client_name: str | None = None,
        project_title: str | None = None,
    ) -> GenerateCompletionOut:
        """Otomasi kompilasi rantai tugas 100% selesai ke dalam Work Completion."""
        pm_emp_id = UUID(current_user.employee_id) if current_user.employee_id else None
        res = await self.repo.generate_completion_from_chain(
            item_id=item_id,
            pm_employee_id=pm_emp_id,
            client_name=client_name,
            project_title=project_title,
        )
        if not res:
            raise AppError("NOT_FOUND", "Gagal mengompilasi Work Completion. Rantai tugas tidak ditemukan.", status=404)

        return GenerateCompletionOut(
            success=res["success"],
            completion_id=res["completion_id"],
            message=res["message"],
            total_target_unit=res["total_target_unit"],
            order_status=res["order_status"],
        )

