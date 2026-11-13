"""
api/tests/modules/face/test_face_unit.py
Uji unit wajah V2 (Milestone 7) tanpa DB: pendaftaran → employee.face_embedding, pencocokan swafoto absen,
dan dampaknya pada absensi (tidak cocok → ditolak online / ditandai offline; layanan mati → PENDING_OM).
"""
from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from app.core.config import settings
from app.core.errors import AppError, ForbiddenError, ValidationError
from app.modules.attendance.services.attendance_session_service import AttendanceSessionService
from app.modules.face.repositories.face_repository import parse_embedding
from app.modules.face.services import face_service as fs
from app.modules.face.services.face_embed_client import EmbedResult, FaceServiceUnavailable
from app.modules.face.services.face_service import FaceOutcome, FaceService, cosine

EMP = uuid4()


@pytest.fixture(autouse=True)
def _real_face_pipeline(monkeypatch):
    """Uji ini memeriksa jalur wajah asli; mode wajah palsu sesi uji dimatikan di sini."""
    monkeypatch.setattr(settings, "FACE_FAKE_MODE", False)


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (120, 90, 30)).save(buf, "JPEG")
    return buf.getvalue()


def _result(vector: list[float] | None, faces: int = 1, quality: float = 0.9) -> EmbedResult:
    return EmbedResult(faces=faces, embedding=vector, quality=quality, detection_score=0.99,
                       model_name="arcface", model_version="1")


def _service(*, embedding=None, role="EMPLOYEE", others=(), results=None, key="k/selfie.jpg"):
    repo = MagicMock()
    repo.employee_of_user = AsyncMock(return_value=SimpleNamespace(employee_id=EMP, role=role,
                                                                   face_embedding=embedding))
    repo.embedding_of = AsyncMock(return_value=embedding)
    repo.other_embeddings = AsyncMock(return_value=[SimpleNamespace(face_embedding=o) for o in others])
    repo.set_embedding = AsyncMock()
    repo.clear_embedding = AsyncMock(return_value=True)
    repo.file_key = AsyncMock(return_value=key)
    client = MagicMock()
    client.embed = AsyncMock(side_effect=results or [])
    return FaceService(repo, client), repo


def test_parse_embedding_accepts_object_and_plain_list():
    assert parse_embedding({"vector": [1, 0], "model": "m"}) == ([1.0, 0.0], {"model": "m"})
    assert parse_embedding("[0.5, 0.5]") == ([0.5, 0.5], {})
    assert parse_embedding(None) == (None, {})
    assert parse_embedding({"foo": 1}) == (None, {})


def test_cosine_and_score():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([1.0], [1.0, 0.0]) == 0.0  # panjang beda → tidak cocok
    assert FaceOutcome("MATCH", 0.8123).score == 81.23
    assert FaceOutcome("UNAVAILABLE", None).score == 0.0


async def test_enroll_stores_normalised_mean():
    svc, repo = _service(results=[_result([1.0, 0.1]), _result([1.0, 0.0]), _result([0.9, 0.1])])
    got = await svc.enroll("u", [_jpeg()] * 3)
    assert got.enrolled and got.images_used == 3
    vector = repo.set_embedding.await_args.args[1]
    assert sum(v * v for v in vector) == pytest.approx(1.0)


async def test_enroll_rules():
    svc, _ = _service(role="TAMU")
    with pytest.raises(ForbiddenError):
        await svc.enroll("u", [_jpeg()] * 3)
    svc, _ = _service()
    with pytest.raises(ValidationError):
        await svc.enroll("u", [_jpeg()] * 2)
    svc, _ = _service(embedding={"vector": [1.0, 0.0]})
    with pytest.raises(AppError) as err:
        await svc.enroll("u", [_jpeg()] * 3)
    assert err.value.code == "FACE_ALREADY_ENROLLED"
    svc, _ = _service(results=[_result(None, faces=2)])
    with pytest.raises(ValidationError):
        await svc.enroll("u", [_jpeg()] * 3)
    svc, _ = _service(results=[_result([1.0, 0.0]), _result([0.0, 1.0]), _result([1.0, 0.0])])
    with pytest.raises(ValidationError):  # foto-foto bukan orang yang sama
        await svc.enroll("u", [_jpeg()] * 3)
    svc, _ = _service(results=FaceServiceUnavailable("mati"))
    with pytest.raises(AppError) as err:
        await svc.enroll("u", [_jpeg()] * 3)
    assert err.value.code == "FACE_SERVICE_UNAVAILABLE"


async def test_enroll_rejects_face_of_another_employee():
    svc, repo = _service(others=[{"vector": [1.0, 0.0]}],
                         results=[_result([1.0, 0.0]), _result([1.0, 0.05]), _result([1.0, 0.02])])
    with pytest.raises(AppError) as err:
        await svc.enroll("u", [_jpeg()] * 3)
    assert err.value.code == "FACE_DUPLICATE"
    repo.set_embedding.assert_not_awaited()


async def test_verify_selfie_outcomes(monkeypatch):
    monkeypatch.setattr(fs.storage, "get_image_bytes", lambda key: b"jpeg")
    enrolled = {"vector": [1.0, 0.0]}
    svc, _ = _service(embedding=enrolled, results=[_result([0.95, 0.05])])
    assert (await svc.verify_selfie(EMP, uuid4())).result == "MATCH"
    svc, _ = _service(embedding=enrolled, results=[_result([0.2, 1.0])])
    assert (await svc.verify_selfie(EMP, uuid4())).result == "MISMATCH"
    svc, _ = _service(embedding=enrolled, results=[_result(None, faces=0)])
    assert (await svc.verify_selfie(EMP, uuid4())).result == "MISMATCH"
    svc, _ = _service(embedding=enrolled, results=FaceServiceUnavailable("mati"))
    assert (await svc.verify_selfie(EMP, uuid4())).result == "UNAVAILABLE"
    svc, _ = _service(embedding=None)
    assert (await svc.verify_selfie(EMP, uuid4())).result == "NOT_ENROLLED"
    svc, _ = _service(embedding=[0.1, 0.2, 0.3, 0.4], results=[_result([1.0, 0.0])])  # seed 4-dimensi lama
    assert (await svc.verify_selfie(EMP, uuid4())).result == "STALE"


def _attendance(outcome: FaceOutcome) -> tuple[AttendanceSessionService, MagicMock]:
    repo = MagicMock()
    repo.flag_missing_face = AsyncMock(return_value="flagged")
    faces = MagicMock()
    faces.verify_selfie = AsyncMock(return_value=outcome)
    return AttendanceSessionService(repo, MagicMock(), faces), repo


async def test_attendance_online_mismatch_is_rejected():
    svc, _ = _attendance(FaceOutcome("MISMATCH", 0.41))
    with pytest.raises(AppError) as err:
        await svc.verify_face(EMP, uuid4(), online=True)
    assert err.value.code == "FACE_MISMATCH"


async def test_attendance_offline_mismatch_and_outage_are_flagged():
    row = SimpleNamespace(id=uuid4())
    svc, repo = _attendance(FaceOutcome("MISMATCH", 0.41))
    outcome = await svc.verify_face(EMP, uuid4(), online=False)
    assert await svc.record_face(row, "CHECK_IN", outcome, online=False) == "flagged"
    assert "tidak cocok" in repo.flag_missing_face.await_args.args[2]
    svc, repo = _attendance(FaceOutcome("UNAVAILABLE", None))
    outcome = await svc.verify_face(EMP, uuid4(), online=True)
    assert await svc.record_face(row, "CHECK_OUT", outcome, online=True) == "flagged"
    assert "tidak tersedia" in repo.flag_missing_face.await_args.args[2]


async def test_attendance_match_is_not_flagged():
    row = SimpleNamespace(id=uuid4())
    svc, repo = _attendance(FaceOutcome("MATCH", 0.93))
    outcome = await svc.verify_face(EMP, uuid4(), online=True)
    assert await svc.record_face(row, "CHECK_IN", outcome, online=True) is row
    repo.flag_missing_face.assert_not_awaited()


async def test_enroll_allowed_for_field_and_office_roles():
    """Pekerja kantor (absen web) boleh mendaftarkan wajah dirinya; lapangan tetap boleh."""
    for peran in ("TEAM_LEADER", "EMPLOYEE", "SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER",
                  "ADMIN_HR_GA", "FINANCE", "HSE"):
        svc, repo = _service(role=peran, results=[_result([1.0, 0.1]), _result([1.0, 0.0]), _result([0.9, 0.1])])
        assert (await svc.enroll("u", [_jpeg()] * 3)).enrolled, peran
        repo.set_embedding.assert_awaited_once()


async def test_enroll_other_roles_forbidden():
    for peran in ("TAMU", "", "LEGACY_ADMIN"):
        svc, repo = _service(role=peran)
        with pytest.raises(ForbiddenError):
            await svc.enroll("u", [_jpeg()] * 3)
        repo.set_embedding.assert_not_awaited()
