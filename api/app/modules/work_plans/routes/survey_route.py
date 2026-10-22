"""
app/modules/work_plans/routes/survey_route.py
Rute survei ACS & CCTV berformat baku (docs/37): ketua tim mengisi titik & laporan lalu mengirim; PM/OM divisi
meninjau dan menyusun item lanjutan. Kedudukan pada jadwal diperiksa di service (check_daily_access).
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.work_plans.controllers.survey_controller import SurveyController
from app.modules.work_plans.schemas.survey_schema import (
    CatalogAddIn,
    LineEditIn,
    PlanFromSurveyIn,
    PlanFromSurveyOut,
    PointIn,
    PointLine,
    PointLocationIn,
    ReportIn,
    ReviewIn,
    SurveyListItem,
    SurveyOut,
)

router = APIRouter(prefix="/work-plans/surveys", tags=["Work Plan Surveys"])
_LOGIN = Depends(get_current_user)
_PLANNER = Depends(require_permission(Permission.CREATE_PLAN))


@router.get("", response_model=list[SurveyListItem])
async def list_surveys(state: Literal["DRAFT", "SUBMITTED", "APPROVED"] | None = None,
                       current_user: CurrentUser = _LOGIN,
                       controller: SurveyController = Depends()) -> list[SurveyListItem]:
    """Daftar survei: ketua/anggota tim (jadwal terbit), PM/OM divisi, admin/OM semua. Saring status."""
    return await controller.list_surveys(current_user, state)


@router.get("/{task_id}", response_model=SurveyOut)
async def get_survey(task_id: UUID, current_user: CurrentUser = _LOGIN,
                     controller: SurveyController = Depends()) -> SurveyOut:
    """Survei: format (ACS/CCTV), slot foto, katalog material, titik, BoM, status."""
    return await controller.detail(current_user, task_id)


@router.post("/{task_id}/points", response_model=SurveyOut, status_code=status.HTTP_201_CREATED)
async def add_point(task_id: UUID, data: PointIn, current_user: CurrentUser = _LOGIN,
                    controller: SurveyController = Depends()) -> SurveyOut:
    """Ketua tim menambah titik: foto per slot, remark, material/kebutuhan/kabel."""
    return await controller.add_point(current_user, task_id, data)


@router.put("/points/{point_id}", response_model=SurveyOut)
async def update_point(point_id: UUID, data: PointIn, current_user: CurrentUser = _LOGIN,
                       controller: SurveyController = Depends()) -> SurveyOut:
    """Ketua tim mengganti isi titik."""
    return await controller.update_point(current_user, point_id, data)


@router.put("/points/{point_id}/location", response_model=SurveyOut)
async def move_point(point_id: UUID, data: PointLocationIn, current_user: CurrentUser = _LOGIN,
                     controller: SurveyController = Depends()) -> SurveyOut:
    """Geser titik di peta layout (PM kapan pun; ketua tim selama survei masih draf)."""
    return await controller.move_point(current_user, point_id, data)


@router.delete("/points/{point_id}", response_model=SurveyOut)
async def delete_point(point_id: UUID, current_user: CurrentUser = _LOGIN,
                       controller: SurveyController = Depends()) -> SurveyOut:
    """Ketua tim menghapus titik."""
    return await controller.delete_point(current_user, point_id)


@router.post("/{task_id}/lines", response_model=SurveyOut)
async def add_general_line(task_id: UUID, data: PointLine, current_user: CurrentUser = _LOGIN,
                           controller: SurveyController = Depends()) -> SurveyOut:
    """Material umum lokasi (bukan milik satu titik): ketua tim saat draf, PM saat meninjau."""
    return await controller.add_general_line(current_user, task_id, data)


@router.put("/lines/{bom_id}", response_model=SurveyOut)
async def edit_line(bom_id: UUID, data: LineEditIn, current_user: CurrentUser = _LOGIN,
                    controller: SurveyController = Depends()) -> SurveyOut:
    """Ubah nama/jumlah/satuan satu baris BoM survei (tercatat di riwayat)."""
    return await controller.edit_line(current_user, bom_id, data)


@router.delete("/lines/{bom_id}", response_model=SurveyOut)
async def delete_line(bom_id: UUID, current_user: CurrentUser = _LOGIN,
                      controller: SurveyController = Depends()) -> SurveyOut:
    """Hapus satu baris BoM survei (tercatat di riwayat)."""
    return await controller.delete_line(current_user, bom_id)


@router.post("/{task_id}/catalog", response_model=SurveyOut)
async def add_to_catalog(task_id: UUID, data: CatalogAddIn, current_user: CurrentUser = _LOGIN,
                         controller: SurveyController = Depends()) -> SurveyOut:
    """PM menyimpan material di luar katalog ke katalog jenis titik."""
    return await controller.add_to_catalog(current_user, task_id, data)


@router.put("/{task_id}/report", response_model=SurveyOut)
async def save_report(task_id: UUID, data: ReportIn, current_user: CurrentUser = _LOGIN,
                      controller: SurveyController = Depends()) -> SurveyOut:
    """Ketua tim mengisi narasi, tujuan, lokasi, dan gambar layout."""
    return await controller.save_report(current_user, task_id, data)


@router.post("/{task_id}/submit", response_model=SurveyOut)
async def submit_survey(task_id: UUID, current_user: CurrentUser = _LOGIN,
                        controller: SurveyController = Depends()) -> SurveyOut:
    """Ketua tim mengirim survei (semua titik berfoto, slot wajib lengkap)."""
    return await controller.submit(current_user, task_id)


@router.post("/{task_id}/review", response_model=SurveyOut)
async def review_survey(task_id: UUID, data: ReviewIn, current_user: CurrentUser = _PLANNER,
                        controller: SurveyController = Depends()) -> SurveyOut:
    """PM/OM divisi menyetujui atau mengembalikan survei."""
    return await controller.review(current_user, task_id, data)


@router.post("/{task_id}/plan", response_model=PlanFromSurveyOut, status_code=status.HTTP_201_CREATED)
async def plan_from_survey(task_id: UUID, data: PlanFromSurveyIn, current_user: CurrentUser = _PLANNER,
                           controller: SurveyController = Depends()) -> PlanFromSurveyOut:
    """PM/OM divisi menyusun item lanjutan per titik dari survei yang disetujui."""
    return await controller.plan(current_user, task_id, data)
