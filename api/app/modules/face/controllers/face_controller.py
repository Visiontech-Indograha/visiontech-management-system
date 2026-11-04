"""
app/modules/face/controllers/face_controller.py

Controller wajah V2: kebijakan, status, pendaftaran milik sendiri, dan reset oleh pengelola karyawan.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import Depends, UploadFile

from app.core.errors import AppError, ValidationError
from app.core.security import CurrentUser
from app.modules.face.dependencies import get_face_service
from app.modules.face.schemas.face_schema import EnrollResponse, FacePolicy, FaceResetResponse, FaceStatus
from app.modules.face.services.face_service import ENROLL_MAX, MAX_IMAGE_BYTES, FaceService


async def _read_image(upload: UploadFile) -> bytes:
    """Baca unggahan paling banyak batas + 1 bita: berkas raksasa tidak pernah dimuat utuh ke memori."""
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise AppError("FILE_TOO_LARGE", "Ukuran gambar melebihi 5 MB.", status=413)
    return data


class FaceController:
    """Controller use case pengenalan wajah."""

    def __init__(self, face_service: FaceService = Depends(get_face_service)) -> None:
        self.service = face_service

    def handle_get_policy(self) -> FacePolicy:
        return self.service.policy()

    async def handle_get_status(self, current_user: CurrentUser) -> FaceStatus:
        return await self.service.status(current_user.user_id)

    async def handle_enroll(self, current_user: CurrentUser, files: list[UploadFile]) -> EnrollResponse:
        if len(files) > ENROLL_MAX:
            raise ValidationError(f"Maksimal {ENROLL_MAX} foto untuk pendaftaran wajah.")
        images = [await _read_image(f) for f in files]
        return await self.service.enroll(current_user.user_id, images)

    async def handle_admin_status(self, employee_id: UUID) -> FaceStatus:
        return await self.service.status_of_employee(employee_id)

    async def handle_reset(self, current_user: CurrentUser, employee_id: UUID) -> FaceResetResponse:
        await self.service.reset(employee_id, current_user)
        return FaceResetResponse(employee_id=employee_id, enrolled=False)
