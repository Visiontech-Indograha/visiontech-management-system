"""
V-08 · Rujukan di badan permintaan harus milik organisasi pengguna. Id organisasi lain → 404
(keberadaannya tidak dibocorkan) dan **tidak ada baris tersimpan** (tulis → baca ulang).
FK di basis data hanya memeriksa bahwa barisnya ada, bukan milik siapa.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _file(client, world: World, who: str = "member") -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (120, 30, 60)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("bukti.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _asset(client, world: World, code: str) -> str:
    created = client.post("/assets", headers=world.headers(client, "asset"),
                          json={"kind": "TOOL", "code": code, "name": "Tangga lipat", "condition": "BAIK"})
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _count(sql: str, *params) -> int:
    return sync_query(sql, params)[0][0]


def _not_found(response) -> None:
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ── Insiden & laporan harian ──────────────────────────────────────────────────────────────────
def test_incident_for_a_plan_of_another_organisation_is_rejected(client, world, other_world):
    foreign_plan, _ = create_draft_plan(client, other_world)

    response = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": foreign_plan, "occurred_on": jakarta_now().date().isoformat(), "category": "K3_RINGAN",
        "severity": "RENDAH", "description": "Tangga licin di area kerja"})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.incident_report WHERE work_plan_id = %s", foreign_plan) == 0


def test_incident_with_evidence_of_another_organisation_is_rejected(client, world, other_world, fake_storage):
    plan_id, _ = run_plan_to_in_progress(client, world)
    foreign_file = _file(client, other_world)

    response = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "occurred_on": jakarta_now().date().isoformat(), "category": "K3_RINGAN",
        "severity": "RENDAH", "description": "Tangga licin di area kerja", "evidence_file_ids": [foreign_file]})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.incident_report WHERE work_plan_id = %s", plan_id) == 0


def test_daily_report_with_evidence_of_another_organisation_is_rejected(client, world, other_world, fake_storage):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    foreign_file = _file(client, other_world)

    response = client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=world.headers(client, "leader"), json={
        "body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada", "evidence_file_ids": [foreign_file]})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.daily_report WHERE work_plan_day_id = %s", day_ids[0]) == 0


# ── Aset ──────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("foreign", ["asset_id", "work_plan_id", "driver_employee_id"])
def test_allocation_with_a_reference_of_another_organisation_is_rejected(client, world, other_world, foreign):
    body = {
        "asset_id": _asset(client, world, "TL-UJI"),
        "work_plan_id": create_draft_plan(client, world, start_offset_days=7)[0],
        "driver_employee_id": world.employees["member"],
    }
    body[foreign] = {
        "asset_id": lambda: _asset(client, other_world, "TL-ASING"),
        "work_plan_id": lambda: create_draft_plan(client, other_world, start_offset_days=7)[0],
        "driver_employee_id": lambda: other_world.employees["member"],
    }[foreign]()

    asset_id = body.pop("asset_id")
    response = client.post(f"/assets/{asset_id}/reserve", headers=world.headers(client, "asset"), json=body)

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.asset_allocation WHERE asset_id = %s", asset_id) == 0
    assert _count("SELECT count(*) FROM vms.asset WHERE id = %s AND status = 'AVAILABLE'", asset_id) == 1


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
def test_employee_in_a_unit_of_another_organisation_is_rejected(client, world, other_world):
    response = client.post("/employees", headers=world.headers(client, "hr"), json={
        "employee_no": "ASING-01", "full_name": "Karyawan unit asing", "position": "Teknisi",
        "unit_id": other_world.unit_id, "join_date": "2026-01-05"})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.employee WHERE organization_id = %s AND employee_no = 'ASING-01'",
                  world.org_id) == 0


def test_assignment_to_a_unit_of_another_organisation_is_rejected(client, world, other_world):
    emp = world.employees["member"]
    before = _count("SELECT count(*) FROM vms.employee_assignment WHERE employee_id = %s", emp)

    response = client.post(f"/employees/{emp}/assignments", headers=world.headers(client, "hr"), json={
        "position": "Supervisor", "unit_id": other_world.unit_id, "valid_from": jakarta_now().date().isoformat()})

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.employee_assignment WHERE employee_id = %s", emp) == before


# ── SK ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("foreign", ["site_id", "pm_employee_id", "leader_employee_id"])
def test_plan_with_a_reference_of_another_organisation_is_rejected(client, world, other_world, foreign):
    start = jakarta_now().date().isoformat()
    body = {"title": "SK rujukan asing", "unit_id": world.unit_id, "site_id": world.site_id,
            "location_text": "Gudang uji", "period_start": start, "period_end": start,
            "pm_employee_id": world.employees["pm"], "leader_employee_id": world.employees["leader"]}
    body[foreign] = other_world.site_id if foreign == "site_id" else other_world.employees["leader"]

    response = client.post("/work-plans", headers=world.headers(client, "pm"), json=body)

    _not_found(response)
    assert _count("SELECT count(*) FROM vms.work_plan WHERE organization_id = %s AND title = 'SK rujukan asing'",
                  world.org_id) == 0


@pytest.mark.parametrize("foreign", ["site_id", "leader_employee_id"])
def test_plan_update_with_a_reference_of_another_organisation_is_rejected(client, world, other_world, foreign):
    plan_id, _ = create_draft_plan(client, world)
    before = sync_query("SELECT site_id, leader_employee_id, row_version FROM vms.work_plan WHERE id = %s", (plan_id,))
    value = other_world.site_id if foreign == "site_id" else other_world.employees["leader"]

    response = client.patch(f"/work-plans/{plan_id}", headers=world.headers(client, "pm"),
                          json={foreign: value, "row_version": before[0][2]})

    _not_found(response)
    assert sync_query("SELECT site_id, leader_employee_id, row_version FROM vms.work_plan WHERE id = %s",
                      (plan_id,)) == before
