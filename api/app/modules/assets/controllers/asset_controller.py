"""
app/modules/assets/controllers/asset_controller.py

Controller orkestrasi use case manajemen aset, pemesanan, dan BAST pengembalian.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool

from app.api.deps import get_asset_reservation_service
from app.core.security import CurrentUser
from app.modules.assets.schemas.asset_schema import (
    AssetAllocationResponse,
    AssetCheckRequest,
    AssetCreate,
    AssetListItem,
    AssetReleaseRequest,
    AssetReserveRequest,
    AssetResponse,
    AssetReturnCreate,
    AssetReturnHistoryItem,
    AssetReturnResponse,
    AssetReturnVerify,
    AssetStatusResponse,
    PlanAssetItem,
)
from app.modules.assets.services.asset_service import AssetReservationService
from app.shared.access.access_service import PlanAccess
from app.shared.documents.pdf_service import html_to_pdf, render_bast_html


class AssetController:
    """
    Controller use case aset organisasi, reservasi penugasan SK, pengecekan kendaraan, dan BAST.
    """

    def __init__(
        self,
        asset_reservation_service: AssetReservationService = Depends(get_asset_reservation_service),
    ) -> None:
        self.service = asset_reservation_service

    async def handle_create_asset(self, current_user: CurrentUser, data: AssetCreate) -> AssetResponse:
        """Membuat aset baru dalam organisasi."""
        try:
            row = await self.service.create_asset(
                current_user.organization_id,
                kind=data.kind,
                vehicle_type=data.vehicle_type,
                code=data.code,
                name=data.name,
                condition=data.condition,
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={"code": "DB_ERROR", "message": str(e)},
            ) from e
        return AssetResponse(**row._mapping)

    async def handle_list_assets(self, current_user: CurrentUser) -> list[AssetListItem]:
        """Mengambil daftar ringkasan aset organisasi beserta alokasi aktifnya."""
        rows = await self.service.list_assets(current_user.organization_id)
        return [AssetListItem(**r._mapping) for r in rows]

    async def handle_return_history(self, current_user: CurrentUser, asset_id: UUID) -> list[AssetReturnHistoryItem]:
        """Mengambil riwayat pengembalian aset."""
        rows = await self.service.return_history(current_user.organization_id, asset_id)
        return [AssetReturnHistoryItem(**r._mapping) for r in rows]

    async def handle_bast_pdf(self, current_user: CurrentUser, return_id: UUID) -> Response:
        """Menghasilkan file PDF Berita Acara Serah Terima (BAST) pengembalian aset."""
        record = await self.service.bast(current_user.organization_id, return_id)
        pdf = await run_in_threadpool(html_to_pdf, render_bast_html(record))
        filename = f"BAST-{record.asset_code}-{record.plan_number}.pdf".replace("/", "-")
        return Response(
            pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    async def handle_reserve(
        self, current_user: CurrentUser, asset_id: UUID, data: AssetReserveRequest
    ) -> AssetAllocationResponse:
        """Memesan aset untuk work plan yang aktif."""
        await self.service.ensure_refs(
            current_user.organization_id,
            assets=[asset_id],
            work_plans=[data.work_plan_id],
            employees=[data.driver_employee_id],
        )
        allocation = await self.service.reserve(current_user, asset_id, data.work_plan_id, data.driver_employee_id)
        return AssetAllocationResponse(**allocation._mapping)

    async def handle_release(
        self, current_user: CurrentUser, asset_id: UUID, data: AssetReleaseRequest
    ) -> AssetStatusResponse:
        """Melepas alokasi aset yang belum digunakan."""
        await self.service.ensure_refs(
            current_user.organization_id,
            assets=[asset_id],
            work_plans=[data.work_plan_id],
        )
        status_ = await self.service.release(current_user, asset_id, data.work_plan_id)
        return AssetStatusResponse(asset_id=asset_id, status=status_)

    async def handle_check(
        self, current_user: CurrentUser, asset_id: UUID, data: AssetCheckRequest
    ) -> AssetStatusResponse:
        """Pengecekan kelayakan kondisi kendaraan oleh pengemudi."""
        await self.service.ensure_refs(current_user.organization_id, assets=[asset_id])
        status_ = await self.service.check(current_user, asset_id, data.decision, data.reason)
        return AssetStatusResponse(asset_id=asset_id, status=status_)

    async def handle_request_return(
        self, access: PlanAccess, alloc_id: UUID, data: AssetReturnCreate
    ) -> AssetReturnResponse:
        """Mengajukan pengembalian aset oleh ketua tim SK."""
        row = await self.service.request_return(access.user, alloc_id, data.condition_on_return, data.note)
        return AssetReturnResponse(**row._mapping)

    async def handle_verify_return(
        self, current_user: CurrentUser, return_id: UUID, data: AssetReturnVerify
    ) -> AssetReturnResponse:
        """Verifikasi BAST pengembalian aset oleh petugas OPS/Aset."""
        row = await self.service.verify_return(current_user, return_id, data.is_accepted, data.note)
        return AssetReturnResponse(**row._mapping)

    async def handle_plan_assets(self, plan_id: UUID) -> list[PlanAssetItem]:
        """Mengambil daftar aset yang digunakan pada satu work plan."""
        rows = await self.service.plan_assets(plan_id)
        return [PlanAssetItem(**r._mapping) for r in rows]
