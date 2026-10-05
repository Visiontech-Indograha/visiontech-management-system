"""
api/tests/test_face_unit.py
Pengujian unit murni (tanpa ketergantungan DB) untuk skema, klien, dan logika layanan Face Recognition.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.errors import ValidationError
from app.crud.crud_face import parse_vector
from app.schemas.face import (
    ConsentRequest,
    FaceLiveness,
    FacePolicy,
    TemplateResponse,
)
from app.services.face_embed_client import FaceEmbedClient
from app.services.face_service import POLICY_TEXT, POLICY_VERSION, FaceService, _cosine, _normalize


def test_face_service_math():
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    assert _cosine(v1, v2) == 0.0
    assert _cosine(v1, v1) == 1.0
    norm = _normalize([3.0, 4.0])
    assert pytest.approx(norm[0]) == 0.6
    assert pytest.approx(norm[1]) == 0.8


def test_face_policy():
    policy = FacePolicy(version=POLICY_VERSION, text=POLICY_TEXT)
    assert policy.version == "2026-10-05"
    assert "HANYA untuk absensi masuk dan pulang" in policy.text


def test_consent_request_valid():
    req = ConsentRequest(state="GRANTED", policy_version="2026-10-05")
    assert req.state == "GRANTED"
    assert req.policy_version == "2026-10-05"


def test_face_liveness():
    live = FaceLiveness(challenges=["BLINK", "TURN_LEFT"], passed=True)
    assert live.passed is True
    assert len(live.challenges) == 2


def test_template_response():
    now = datetime.now(UTC)
    vec = [0.1] * 512
    resp = TemplateResponse(
        model_name="buffalo_s",
        model_version="w600k_mbf",
        enrollment_version="v1",
        embeddings=[vec],
        expires_at=now,
    )
    assert len(resp.embeddings[0]) == 512
    assert resp.model_name == "buffalo_s"


def test_parse_vector():
    raw = "[0.123, -0.456, 0.789]"
    parsed = parse_vector(raw)
    assert parsed is not None
    assert len(parsed) == 3
    assert pytest.approx(parsed[0]) == 0.123
    assert pytest.approx(parsed[1]) == -0.456
    assert pytest.approx(parsed[2]) == 0.789


def test_parse_vector_none():
    assert parse_vector(None) is None
    assert parse_vector("") is None


def test_face_embed_client_attributes():
    client = FaceEmbedClient(base_url="http://face:8000", token="secret-token")
    assert client.base_url == "http://face:8000"
    assert client.token == "secret-token"


@pytest.mark.anyio
async def test_face_service_enroll_count_validation():
    repo = MagicMock()
    repo.employee_of_user = AsyncMock(return_value=MagicMock(employee_id=uuid4(), attendance_mode="MOBILE"))
    repo.latest_consent = AsyncMock(return_value=MagicMock(state="GRANTED"))
    service = FaceService(repo=repo, client=None)  # type: ignore
    # Kurang dari ENROLL_MIN (3)
    with pytest.raises(ValidationError) as exc:
        await service.enroll("org-1", "user-1", [b"fake1", b"fake2"], FaceLiveness(passed=True))
    assert "3 sampai 5 foto" in str(exc.value)

    # Lebih dari ENROLL_MAX (5)
    with pytest.raises(ValidationError) as exc:
        await service.enroll(
            "org-1", "user-1",
            [b"1", b"2", b"3", b"4", b"5", b"6"],
            FaceLiveness(passed=True)
        )
    assert "3 sampai 5 foto" in str(exc.value)
