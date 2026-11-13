"""
Absen web pekerja kantor: kode alasan terpisah, akurasi kasar -> menunggu HR kantor, HP tidak berubah.
Unit (tanpa DB) untuk alasan; kelas DB untuk alur lengkap.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.attendance.services.attendance_session_service import (
    AttendanceRowWithEncouragement,
    AttendanceSessionService,
    location_decision,
    review_reasons,
)
from app.modules.face.services.face_service import FaceOutcome


def test_reasons_are_separate_codes():
    assert review_reasons(FaceOutcome("NOT_ENROLLED", None), outside=False, coarse=False) == ["FACE_NOT_ENROLLED"]
    assert review_reasons(FaceOutcome("MISMATCH", 0.4), outside=False, coarse=False) == ["FACE_MISMATCH"]
    assert review_reasons(FaceOutcome("UNAVAILABLE", None), outside=False, coarse=False) == ["FACE_UNAVAILABLE"]
    assert review_reasons(FaceOutcome("MATCH", 0.95), outside=True, coarse=False) == ["LOKASI_DI_LUAR_ZONA"]
    assert review_reasons(FaceOutcome("MATCH", 0.95), outside=True, coarse=True) == ["LOKASI_KASAR"]
    assert review_reasons(FaceOutcome("NOT_ENROLLED", None), outside=False, coarse=True) == [
        "FACE_NOT_ENROLLED", "LOKASI_KASAR"]
    assert review_reasons(FaceOutcome("MATCH", 0.95), outside=False, coarse=False) == []
    assert review_reasons(None, outside=False, coarse=False) == []


def test_location_decision():
    assert location_decision(outside=False, coarse=False) == "ACCEPTED"
    assert location_decision(outside=True, coarse=False) == "OUTSIDE_ZONE"
    assert location_decision(outside=False, coarse=True) == "PENDING_COARSE"
    assert location_decision(outside=True, coarse=True) == "PENDING_COARSE"


@pytest.mark.parametrize(("mode", "channel", "acc", "expected"), [
    ("OFFICE", "WEB", 301, True),
    ("OFFICE", "WEB", 300, False),
    ("OFFICE", "WEB", None, False),
    ("FIELD", "MOBILE", 5000, False),   # HP lapangan: tetap ditolak lewat aturan lama
    ("FIELD", "WEB", 5000, False),
    ("OFFICE", "MOBILE", 5000, False),
])
def test_coarse_only_for_office_worker_on_web(mode, channel, acc, expected):
    worker = SimpleNamespace(attendance_mode=mode)
    assert AttendanceSessionService._is_coarse_office_web(worker, channel, acc) is expected


def test_row_wrapper_exposes_extra_fields():
    row = SimpleNamespace(_mapping={"id": uuid4()}, employee_id=uuid4())
    wrapped = AttendanceRowWithEncouragement(row, None, {"review_reasons": ["LOKASI_KASAR"]})
    assert wrapped._mapping["review_reasons"] == ["LOKASI_KASAR"]
    assert wrapped.review_reasons == ["LOKASI_KASAR"]
    assert wrapped.employee_id == row.employee_id


async def test_mobile_field_worker_coarse_still_rejected():
    from app.core.errors import AppError

    repo = MagicMock()
    repo.attendance_mode_of = AsyncMock(return_value=SimpleNamespace(
        employee_id=uuid4(), attendance_mode="FIELD", unit_id=None, is_admin=False))
    svc = AttendanceSessionService(repo, MagicMock(), None)
    with pytest.raises(AppError) as err:
        await svc.check_in("org", "u", site_id=uuid4(), lng=1.0, lat=1.0, origin="GPS", selfie_file_id=uuid4(),
                           accuracy_m=150.0, channel="MOBILE", online=False)
    assert err.value.code == "GPS_INACCURATE"
