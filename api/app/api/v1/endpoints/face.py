"""
app/api/v1/endpoints/face.py
Endpoint pengenalan wajah untuk absensi HP (docs/06 fase 8, docs/08 §6).
Hanya untuk pekerja lapangan (FIELD) pada akun sendiri.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_current_user, get_face_service
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
from app.services.face_service import FaceService

router = APIRouter(prefix="/face", tags=["Face"])


@router.get("/policy", response_model=FacePolicy)
def get_face_policy(
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> FacePolicy:
    """Mengambil versi dan teks kebijakan persetujuan biometrik server saat ini."""
    return face_service.policy()


@router.get("/status", response_model=FaceStatus)
async def get_face_status(
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> FaceStatus:
    """
    Status pengenalan wajah pengguna saat ini: persetujuan biometrik, status pendaftaran,
    versi template, dan kebijakan aktif.
    """
    return await face_service.status(current_user.organization_id, current_user.user_id)


@router.post("/consent")
async def set_face_consent(
    body: ConsentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> dict[str, str]:
    """
    Menyetujui atau menarik persetujuan pemakaian data biometrik wajah.
    Menarik persetujuan otomatis menonaktifkan seluruh embedding wajah aktif seketika di database.
    """
    await face_service.set_consent(current_user.user_id, body)
    msg = (
        "Persetujuan biometrik dicatat."
        if body.state == "GRANTED"
        else "Persetujuan biometrik ditarik."
    )
    return {"message": msg}


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_face(
    files: list[UploadFile] = File(...),
    liveness: str = Form("{}"),
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> EnrollResponse:
    """
    Mendaftarkan 3-5 foto pose wajah karyawan.
    Validasi deteksi tunggal, kualitas, konsistensi antar pose, dan pengecekan anti-duplikat dengan karyawan lain.
    """
    images = [await f.read() for f in files]
    try:
        live_data = json.loads(liveness) if liveness else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        live_data = {}
    liveness_obj = FaceLiveness(**live_data)
    return await face_service.enroll(current_user.organization_id, current_user.user_id, images, liveness_obj)


@router.get("/template", response_model=TemplateResponse)
async def get_face_template(
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> TemplateResponse:
    """
    Mengunduh embedding wajah milik sendiri untuk disimpan terenkripsi di HP (absen luring).
    Dibatasi rate-limit (10 unduhan/jam) dan hanya untuk pengguna dengan persetujuan aktif.
    """
    return await face_service.template(current_user.user_id)


@router.post("/probe", response_model=ProbeResponse)
async def create_face_probe(
    file: UploadFile = File(...),
    liveness: str = Form("{}"),
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> ProbeResponse:
    """
    Mengunggah gambar wajah sementara untuk diverifikasi saat check-in atau check-out.
    Mengembalikan probe_id yang diteruskan pada permintaan absensi.
    """
    image = await file.read()
    try:
        live_data = json.loads(liveness) if liveness else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        live_data = {}
    liveness_obj = FaceLiveness(**live_data)
    return await face_service.create_probe(current_user.organization_id, current_user.user_id, image, liveness_obj)


@router.post("/challenge-check", response_model=ChallengeCheckResponse)
async def check_face_challenge(
    file: UploadFile = File(...),
    challenge: str = Form(...),
    current_user: CurrentUser = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> ChallengeCheckResponse:
    """
    Memeriksa gambar langsung dari kamera HP untuk memvalidasi tantangan liveness.
    """
    image = await file.read()
    return await face_service.check_challenge(image, challenge)
