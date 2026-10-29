"""Uji wajah palsu DEV (FACE_FAKE_MODE) dan penandaan absen yang tidak diverifikasi (F8).

Tanpa DB: repositori dan face-service di-mock seperti test_face_unit.py.
"""
from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from app.core.config import settings
from app.modules.attendance.services.attendance_session_service import (
    AttendanceSessionService,
    face_status_of,
)
from app.modules.face.services import face_service as fs
from app.modules.face.services.face_service import FaceOutcome, FaceService, fake_embedding

EMP = uuid4()


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (120, 90, 30)).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def fake_dev(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "FACE_FAKE_MODE", True)


def _face_service(embedding=None) -> tuple[FaceService, MagicMock]:
    repo = MagicMock()
    repo.employee_of_user = AsyncMock(return_value=SimpleNamespace(employee_id=EMP, role="EMPLOYEE",
                                                                   face_embedding=embedding))
    repo.embedding_of = AsyncMock(return_value=embedding)
    repo.other_embeddings = AsyncMock(return_value=[])
    repo.set_embedding = AsyncMock()
    repo.file_key = AsyncMock(return_value="k/selfie.jpg")
    client = MagicMock()
    client.embed = AsyncMock(side_effect=AssertionError("face-service tidak boleh dipanggil dalam mode wajah palsu"))
    return FaceService(repo, client), repo


def test_fake_embedding_is_deterministic_and_normalised():
    first, second = fake_embedding(EMP), fake_embedding(EMP)
    assert first == second
    assert len(first) == 512
    assert sum(v * v for v in first) == pytest.approx(1.0)
    assert fake_embedding(uuid4()) != first  # beda karyawan, beda embedding


async def test_fake_mode_enroll_stores_synthetic_embedding_without_face_service(fake_dev):
    svc, repo = _face_service()
    got = await svc.enroll("u", [_jpeg()] * 3)
    assert got.enrolled and got.images_used == 3
    args = repo.set_embedding.await_args.args
    assert args[1] == fake_embedding(EMP)
    assert args[2] == fs.FAKE_MODEL


async def test_fake_mode_selfie_of_enrolled_employee_matches(fake_dev):
    svc, _ = _face_service(embedding={"vector": fake_embedding(EMP), "model": fs.FAKE_MODEL})
    outcome = await svc.verify_selfie(EMP, uuid4())
    assert outcome.result == "MATCH"
    assert outcome.score == pytest.approx(95.0)
    assert face_status_of(outcome) == "MATCHED"


async def test_fake_mode_without_enrollment_is_not_enrolled(fake_dev):
    svc, _ = _face_service(embedding=None)
    outcome = await svc.verify_selfie(EMP, uuid4())
    assert outcome.result == "NOT_ENROLLED"
    assert face_status_of(outcome) == "NOT_ENROLLED"


def test_fake_mode_is_inactive_outside_development(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "FACE_FAKE_MODE", True)
    assert fs.fake_mode_active() is False


def test_face_status_mapping():
    assert face_status_of(None) == "NOT_CHECKED"
    assert face_status_of(FaceOutcome("MATCH", 0.93)) == "MATCHED"
    assert face_status_of(FaceOutcome("MISMATCH", 0.41)) == "MISMATCH"
    assert face_status_of(FaceOutcome("UNAVAILABLE", None)) == "SERVICE_DOWN"
    assert face_status_of(FaceOutcome("NOT_ENROLLED", None)) == "NOT_ENROLLED"
    assert face_status_of(FaceOutcome("STALE", None)) == "STALE"


def _attendance(outcome, *, enrollment_required: bool, monkeypatch) -> tuple[AttendanceSessionService, MagicMock]:
    monkeypatch.setattr(settings, "FACE_ENROLLMENT_REQUIRED", enrollment_required)
    repo = MagicMock()
    repo.flag_missing_face = AsyncMock(return_value="flagged")
    faces = MagicMock()
    faces.verify_selfie = AsyncMock(return_value=outcome)
    return AttendanceSessionService(repo, MagicMock(), faces), repo


async def test_online_without_enrollment_is_flagged_when_enrollment_flag_is_off(monkeypatch):
    """F8: dengan FACE_ENROLLMENT_REQUIRED=false absen tanpa wajah terdaftar tidak boleh lolos diam-diam."""
    row = SimpleNamespace(id=uuid4())
    svc, repo = _attendance(FaceOutcome("NOT_ENROLLED", None), enrollment_required=False, monkeypatch=monkeypatch)
    outcome = await svc.verify_face(EMP, uuid4(), online=True)
    assert await svc.record_face(row, "CHECK_IN", outcome, online=True) == "flagged"
    assert "belum mendaftar wajah" in repo.flag_missing_face.await_args.args[2]


async def test_unchecked_face_is_flagged_not_silently_passed(monkeypatch):
    row = SimpleNamespace(id=uuid4())
    svc, repo = _attendance(None, enrollment_required=False, monkeypatch=monkeypatch)
    outcome = await svc.verify_face(EMP, None, online=True)
    assert await svc.record_face(row, "CHECK_IN", outcome, online=True) == "flagged"
    assert "tidak diperiksa" in repo.flag_missing_face.await_args.args[2]


async def test_matched_face_is_not_flagged(monkeypatch):
    row = SimpleNamespace(id=uuid4())
    svc, repo = _attendance(FaceOutcome("MATCH", 0.95), enrollment_required=False, monkeypatch=monkeypatch)
    outcome = await svc.verify_face(EMP, uuid4(), online=True)
    assert await svc.record_face(row, "CHECK_IN", outcome, online=True) is row
    repo.flag_missing_face.assert_not_awaited()
