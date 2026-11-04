"""Foto bukti (terlambat / di luar radius) terpisah dari swafoto wajah."""
from uuid import uuid4

from app.modules.attendance.schemas.attendance_schema import CheckInRequest, CheckOutRequest


def _loc():
    return {"lat": 1.0, "lng": 101.0}


def test_check_in_accepts_evidence_and_old_clients_without_it():
    sid, eid = uuid4(), uuid4()
    new = CheckInRequest(site_id=uuid4(), location=_loc(), selfie_file_id=sid, evidence_file_id=eid)
    assert new.evidence_file_id == eid and new.selfie_file_id == sid
    old = CheckInRequest(site_id=uuid4(), location=_loc(), selfie_file_id=sid)
    assert old.evidence_file_id is None


def test_check_out_accepts_evidence():
    eid = uuid4()
    assert CheckOutRequest(location=_loc(), evidence_file_id=eid).evidence_file_id == eid
    assert CheckOutRequest(location=_loc()).evidence_file_id is None
