"""
app/modules/face/routes/face_route.py

Rute HTTP untuk use case pengenalan wajah biometrik dan liveness verification.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.face.controllers.face_controller import FaceController
from app.modules.face.schemas.face_schema import (
    ChallengeCheckResponse,
    ConsentRequest,
    EnrollResponse,
    FacePolicy,
    FaceStatus,
    ProbeResponse,
    TemplateResponse,
)

router = APIRouter(prefix="/face", tags=["Face"])


@router.get("/policy", response_model=FacePolicy)
def get_face_policy(
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> FacePolicy:
    """Mengambil versi dan teks kebijakan persetujuan biometrik server saat ini."""
    return controller.handle_get_policy(current_user)


@router.get("/status", response_model=FaceStatus)
async def get_face_status(
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> FaceStatus:
    """Status pengenalan wajah pengguna saat ini: persetujuan, template, dan status aktif."""
    return await controller.handle_get_status(current_user)


@router.post("/consent")
async def set_face_consent(
    body: ConsentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> dict[str, str]:
    """Menyetujui atau menarik persetujuan pemakaian data biometrik wajah."""
    return await controller.handle_set_consent(current_user, body)


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_face(
    files: list[UploadFile] = File(...),
    liveness: str = Form("{}"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> EnrollResponse:
    """Mendaftarkan 3-5 foto pose wajah karyawan."""
    return await controller.handle_enroll(current_user, files, liveness)


@router.get("/template", response_model=TemplateResponse)
async def get_face_template(
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> TemplateResponse:
    """Mengunduh embedding wajah milik sendiri untuk disimpan terenkripsi di HP."""
    return await controller.handle_get_template(current_user)


@router.post("/probe", response_model=ProbeResponse)
async def create_face_probe(
    file: UploadFile = File(...),
    liveness: str = Form("{}"),
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> ProbeResponse:
    """Mengunggah gambar wajah sementara untuk diverifikasi saat check-in atau check-out."""
    return await controller.handle_create_probe(current_user, file, liveness)


@router.post("/challenge-check")
async def check_face_challenge(
    file: UploadFile = File(...),
    challenge: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    controller: FaceController = Depends(),
) -> ChallengeCheckResponse:
    """Memeriksa gambar langsung dari kamera HP untuk memvalidasi tantangan liveness."""
    return await controller.handle_challenge_check(current_user, file, challenge)
