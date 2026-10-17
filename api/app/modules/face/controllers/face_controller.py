"""
app/modules/face/controllers/face_controller.py

Controller orkestrasi endpoint pengenalan wajah biometrik, persetujuan, pendaftaran, dan probe.
"""
from __future__ import annotations

import json

from fastapi import Depends, UploadFile

from app.api.deps import get_face_service
from app.core.errors import AppError, ValidationError
from app.core.permissions import RoleCode
from app.core.security import CurrentUser
from app.schemas.face import (
    ChallengeCheckResponse,
    ConsentRequest,
    EnrollResponse,
    FaceLiveness,
    FacePolicy,
    FaceStatus,
    ProbeResponse,
    TemplateResponse,
)
from app.services.face_service import ENROLL_MAX, MAX_IMAGE_BYTES, FaceService


async def _read_image(upload: UploadFile) -> bytes:
    """Baca unggahan paling banyak batas + 1 bita: berkas raksasa tidak pernah dimuat utuh ke memori."""
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise AppError("FILE_TOO_LARGE", "Ukuran gambar melebihi 5 MB.", status=413)
    return data


def _liveness(raw: str) -> FaceLiveness:
    """Hasil tantangan dari HP (JSON). Isi tidak valid -> 422, bukan 500; kosong = belum lolos."""
    try:
        return FaceLiveness(**(json.loads(raw) if raw else {}))
    except (ValueError, TypeError):
        raise ValidationError("Pemeriksaan keaslian wajah tidak terbaca. Ulangi pengenalan wajah.") from None


class FaceController:
    """Controller logika use case pengenalan biometrik wajah."""

    def __init__(self, face_service: FaceService = Depends(get_face_service)) -> None:
        self.service = face_service

    def handle_get_policy(self, current_user: CurrentUser) -> FacePolicy:
        """Mengambil versi dan teks kebijakan persetujuan biometrik server saat ini."""
        return self.service.policy()

    async def handle_get_status(self, current_user: CurrentUser) -> FaceStatus:
        """
        Status pengenalan wajah pengguna saat ini: persetujuan biometrik, status pendaftaran,
        versi template, dan kebijakan aktif.
        """
        is_admin = RoleCode.ADMIN in current_user.roles or RoleCode.SUPER_ADMIN in current_user.roles
        return await self.service.status(
            current_user.organization_id,
            current_user.user_id,
            exempt_from_required=is_admin,
        )

    async def handle_set_consent(
        self, current_user: CurrentUser, body: ConsentRequest
    ) -> dict[str, str]:
        """Menyetujui atau menarik persetujuan pemakaian data biometrik wajah."""
        await self.service.set_consent(current_user.user_id, body)
        msg = (
            "Persetujuan biometrik dicatat."
            if body.state == "GRANTED"
            else "Persetujuan biometrik ditarik."
        )
        return {"message": msg}

    async def handle_enroll(
        self,
        current_user: CurrentUser,
        files: list[UploadFile],
        liveness: str,
    ) -> EnrollResponse:
        """Mendaftarkan 3-5 foto pose wajah karyawan."""
        if len(files) > ENROLL_MAX:
            raise ValidationError(f"Maksimal {ENROLL_MAX} foto untuk pendaftaran wajah.")
        liveness_obj = _liveness(liveness)
        images = [await _read_image(f) for f in files]
        return await self.service.enroll(
            current_user.organization_id,
            current_user.user_id,
            images,
            liveness_obj,
        )

    async def handle_get_template(self, current_user: CurrentUser) -> TemplateResponse:
        """Mengunduh embedding wajah milik sendiri untuk disimpan terenkripsi di HP."""
        return await self.service.template(current_user.user_id)

    async def handle_create_probe(
        self,
        current_user: CurrentUser,
        file: UploadFile,
        liveness: str,
    ) -> ProbeResponse:
        """Mengunggah gambar wajah sementara untuk diverifikasi saat check-in atau check-out."""
        liveness_obj = _liveness(liveness)
        image = await _read_image(file)
        return await self.service.create_probe(
            current_user.organization_id,
            current_user.user_id,
            image,
            liveness_obj,
        )

    async def handle_challenge_check(
        self,
        current_user: CurrentUser,
        file: UploadFile,
        challenge: str,
    ) -> ChallengeCheckResponse:
        """Memeriksa gambar langsung dari kamera HP untuk memvalidasi tantangan liveness."""
        image = await _read_image(file)
        return await self.service.check_challenge(current_user.user_id, image, challenge)
