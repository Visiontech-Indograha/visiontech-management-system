"""
V-08 · Rujukan di badan permintaan harus milik organisasi pengguna. Id organisasi lain → 404
(keberadaannya tidak dibocorkan) dan **tidak ada baris tersimpan** (tulis → baca ulang).
FK di basis data hanya memeriksa bahwa barisnya ada, bukan milik siapa.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _file(client, world: World, who: str = "member") -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (120, 30, 60)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("bukti.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _count(sql: str, *params) -> int:
    return sync_query(sql, params)[0][0]


def _not_found(response) -> None:
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ── Insiden & laporan harian ──────────────────────────────────────────────────────────────────


# ── Aset ──────────────────────────────────────────────────────────────────────────────────────


# ── Absensi ───────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("foreign", ["site_id", "selfie_file_id"])
def test_check_in_with_a_reference_of_another_organisation_is_rejected(
        client, world, other_world, fake_storage, foreign):
    body = {"site_id": world.site_id, "location": {"lat": -6.2, "lng": 106.8}, "location_origin": "GPS",
            "selfie_file_id": _file(client, world)}
    body[foreign] = other_world.site_id if foreign == "site_id" else _file(client, other_world)

    response = client.post("/attendance/check-in", headers=world.headers(client, "member"), json=body)

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.attendance WHERE employee_id = %s", world.employees["member"]) == 0


# ── Dokumen pribadi ───────────────────────────────────────────────────────────────────────────
def test_document_with_a_file_of_another_organisation_is_rejected(client, world, other_world, fake_storage):
    own_emp = world.employees["member"]

    response = client.post(f"/employees/{own_emp}/documents", headers=world.headers(client, "hr"),
                           json={"doc_type": "KTP", "number": "3201011234567890", "file_id": _file(client, other_world)})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.employee_document WHERE employee_id = %s", own_emp) == 0


def test_document_for_an_employee_of_another_organisation_is_rejected(client, world, other_world, fake_storage):
    foreign_emp = other_world.employees["member"]

    response = client.post(f"/employees/{foreign_emp}/documents", headers=world.headers(client, "hr"),
                           json={"doc_type": "KTP", "number": "3201011234567890", "file_id": _file(client, world, "hr")})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.employee_document WHERE employee_id = %s", foreign_emp) == 0


# ── Karyawan ──────────────────────────────────────────────────────────────────────────────────
def test_employee_in_a_division_of_another_organisation_is_rejected(client, world, other_world):
    response = client.post("/employees", headers=world.headers(client, "hr"), json={
        "employee_no": "ASING-01", "full_name": "Karyawan divisi asing", "office_id": world.org_id,
        "division_id": other_world.unit_id, "join_date": "2026-01-05"})

    assert response.status_code in (404, 422), response.text
    assert _count("SELECT count(*) FROM employee WHERE employee_no = 'ASING-01'") == 0


# ── SK ────────────────────────────────────────────────────────────────────────────────────────


