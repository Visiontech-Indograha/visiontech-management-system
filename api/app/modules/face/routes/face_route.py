"""
app/modules/face/routes/face_route.py

Rute HTTP wajah V2. Pencocokan swafoto absen terjadi di server saat check-in/out (modul attendance),
tidak ada endpoint probe terpisah.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user, require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.face.controllers.face_controller import FaceController
from app.modules.face.schemas.face_schema import EnrollResponse, FacePolicy, FaceResetResponse, FaceStatus

router = APIRouter(prefix="/face", tags=["Face"])


@router.get("/policy", response_model=FacePolicy)
def get_face_policy(
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> FacePolicy:
    """Ambang kecocokan, kewajiban pendaftaran, dan jumlah foto pendaftaran."""
    return controller.handle_get_policy()


@router.get("/status", response_model=FaceStatus)
async def get_face_status(
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> FaceStatus:
    """Apakah wajah pengguna saat ini sudah terdaftar & wajib terdaftar."""
    return await controller.handle_get_status(current_user)


@router.post("/enroll", response_model=EnrollResponse, status_code=201)
async def enroll_face(
    files: list[UploadFile] = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> EnrollResponse:
    """Mendaftarkan wajah sendiri dari 3–5 foto (sudut berbeda)."""
    return await controller.handle_enroll(current_user, files)


@router.get("/enrollments/{employee_id}/status", response_model=FaceStatus)
async def get_employee_face_status(
    employee_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: FaceController = Depends(),
) -> FaceStatus:
    """Apakah wajah karyawan sudah terdaftar (HR/admin)."""
    return await controller.handle_admin_status(employee_id)


@router.delete("/enrollment/me", response_model=FaceResetResponse)
async def reset_own_face_enrollment(
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> FaceResetResponse:
    """Hapus pendaftaran wajah sendiri (mis. ingin mendaftar ulang); tercatat di log aktivitas."""
    return await controller.handle_reset_own(current_user)


@router.delete("/enrollments/{employee_id}", response_model=FaceResetResponse)
async def reset_face_enrollment(
    employee_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_USERS)),
    controller: FaceController = Depends(),
) -> FaceResetResponse:
    """Hapus pendaftaran wajah karyawan agar ia bisa mendaftar ulang (HR/admin); tercatat di audit."""
    return await controller.handle_reset(current_user, employee_id)
