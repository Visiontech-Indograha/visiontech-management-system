"""
T-15 · Wajah tidak cocok → diperiksa manusia (dok 00 §2.3, K-10, R-02).
PostgreSQL menjalankan trigger BEFORE menurut urutan nama. Trigger wajah harus berjalan SETELAH
geofence, karena geofence menyetel ulang status berdasarkan jarak.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


@pytest.fixture
def employee() -> Iterator[tuple[str, str]]:
    (org,) = sync_query("INSERT INTO vms.organization (name) VALUES ('Organisasi uji trigger') RETURNING id")[0]
    (emp,) = sync_query(
        "INSERT INTO vms.employee (organization_id, employee_no, full_name, position, join_date) "
        "VALUES (%s, %s, 'Karyawan uji', 'Teknisi', '2026-01-05') RETURNING id",
        (org, f"UJI-{uuid.uuid4().hex[:6]}"),
    )[0]
    yield str(org), str(emp)
    sync_query("DELETE FROM vms.attendance WHERE organization_id = %s", (org,))
    sync_query("DELETE FROM vms.organization WHERE id = %s", (org,))


def _insert(org: str, emp: str, face_result: str | None) -> str:
    (status,) = sync_query(
        """INSERT INTO vms.attendance (organization_id, employee_id, work_date, site_label, check_in_at, radius_m, face_result)
           VALUES (%s, %s, '2026-09-23', 'Lokasi uji', '2026-09-23 08:05+07', 100, %s) RETURNING status::text""",
        (org, emp, face_result),
    )[0]
    return status


@pytest.mark.parametrize("face_result", ["NO_MATCH", "LOW_QUALITY"])
def test_face_mismatch_inside_radius_needs_review(employee, face_result):
    assert _insert(*employee, face_result) == "NEEDS_REVIEW"


@pytest.mark.parametrize("face_result", ["MATCH", "NOT_ENROLLED", "SKIPPED", None])
def test_face_ok_or_absent_inside_radius_is_auto_valid(employee, face_result):
    # K-10: tidak terdaftar wajah tidak boleh merugikan karyawan.
    assert _insert(*employee, face_result) == "AUTO_VALID"


def test_face_trigger_fires_after_geofence():
    names = [n for (n,) in sync_query(
        "SELECT tgname FROM pg_trigger WHERE tgrelid = 'vms.attendance'::regclass AND NOT tgisinternal "
        "AND tgtype & 2 = 2 ORDER BY tgname"  # BEFORE triggers, urutan eksekusi = urutan nama
    )]
    face = next(n for n in names if "face" in n)

    assert names.index("attendance_geofence") < names.index(face)
