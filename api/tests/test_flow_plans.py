"""
V-02 · Alur modul yang bergantung pada SK: aset (M6), siklus SK (M3), insiden (M7), laporan harian (M5).

Alur SK & turunannya ditandai `xfail(strict=True)` sampai W2 (V-03…V-06) selesai: begitu alurnya
lulus, xfail ketat membuat uji MERAH sehingga penandanya wajib dicabut — tidak bisa terlupa.
Uji-uji ini sekaligus spesifikasi yang dapat dijalankan untuk W2 (termasuk `PUT /plans/{id}/members`).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

W2 = pytest.mark.xfail(strict=True, reason="Siklus SK belum hidup — V-03…V-06 (PLAN-VERIFIKASI-MODUL-RINCI)")


def _row_version(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def create_draft_plan(client, world: World, start_offset_days: int = 0, length_days: int = 2) -> tuple[str, list[str]]:
    """SK draft lengkap: periode, satu hari kerja per tanggal, masing-masing satu tugas. → (plan_id, day_ids)."""
    start = jakarta_now().date() + timedelta(days=start_offset_days)
    end = start + timedelta(days=length_days - 1)
    pm = world.headers(client, "pm")
    plan = client.post("/plans", headers=pm, json={
        "title": "Instalasi CCTV gudang", "unit_id": world.unit_id, "site_id": world.site_id,
        "location_text": "Gudang uji", "period_start": start.isoformat(), "period_end": end.isoformat(),
        "pm_employee_id": world.employees["pm"], "leader_employee_id": world.employees["leader"]})
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    day_ids = []
    for i in range(length_days):
        day = client.post(f"/plans/{plan_id}/days", headers=pm,
                          json={"work_date": (start + timedelta(days=i)).isoformat(), "title": f"Hari {i + 1}"})
        assert day.status_code == 200, day.text
        day_ids.append(day.json()["id"])
        task = client.post(f"/plans/days/{day_ids[-1]}/tasks", headers=pm, json={"title": "Pasang kamera"})
        assert task.status_code == 200, task.text
    return plan_id, day_ids


def run_plan_to_in_progress(client, world: World) -> tuple[str, list[str]]:
    plan_id, day_ids = create_draft_plan(client, world)
    pm = world.headers(client, "pm")

    members = client.put(f"/plans/{plan_id}/members", headers=pm, json={
        "leader_employee_id": world.employees["leader"],
        "member_employee_ids": [world.employees["member"]], "row_version": _row_version(plan_id)})
    assert members.status_code == 200, members.text

    published = client.post(f"/plans/{plan_id}/publish", headers=pm, json={"row_version": _row_version(plan_id), "reason": ""})
    assert published.status_code == 200, published.text
    assert sync_query("SELECT kind::text, status::text FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,)) \
        == [("INITIAL_ORDER", "AWAITING_ACCEPTANCE")]

    accepted = client.post(f"/plans/{plan_id}/accept", headers=world.headers(client, "leader"),
                           json={"row_version": _row_version(plan_id), "reason": ""})
    assert accepted.status_code == 200, accepted.text
    assert sync_query("SELECT status::text FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,)) == [("EFFECTIVE",)]

    started = client.post(f"/plans/{plan_id}/start", headers=pm, json={"row_version": _row_version(plan_id), "reason": ""})
    assert started.status_code == 200, started.text
    assert sync_query("SELECT status::text FROM vms.work_plan WHERE id = %s", (plan_id,)) == [("IN_PROGRESS",)]
    return plan_id, day_ids


def test_asset_cycle_reserve_return_verify(client, world):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)
    asset_officer = world.headers(client, "asset")

    asset = client.post("/assets", headers=asset_officer,
                        json={"kind": "TOOL", "code": "TL-UJI", "name": "Tangga lipat", "condition": "BAIK"})
    assert asset.status_code == 201, asset.text
    asset_id = asset.json()["id"]

    allocated = client.post("/assets/allocate", headers=asset_officer, json={"asset_id": asset_id, "work_plan_id": plan_id})
    assert allocated.status_code == 200, allocated.text
    alloc_id = allocated.json()["id"]
    assert sync_query("SELECT work_plan_id::text FROM vms.asset_allocation WHERE id = %s", (alloc_id,)) == [(plan_id,)]

    returned = client.post(f"/assets/allocations/{alloc_id}/return", headers=world.headers(client, "leader"),
                           json={"condition_on_return": "BAIK"})
    assert returned.status_code == 200, returned.text
    return_id = returned.json()["id"]

    verified = client.post(f"/assets/returns/{return_id}/verify", headers=asset_officer, json={"is_accepted": True})
    assert verified.status_code == 200, verified.text
    assert sync_query("SELECT count(*) FROM vms.asset_return WHERE id = %s AND verified_at IS NOT NULL", (return_id,)) \
        == [(1,)]


@W2
def test_plan_lifecycle_to_extension(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    pm = world.headers(client, "pm")

    change = client.post(f"/plans/{plan_id}/changes/extension", headers=pm,
                         json={"new_period_end": (jakarta_now().date() + timedelta(days=5)).isoformat(),
                               "reason": "Hujan deras dua hari"})
    assert change.status_code in (200, 201), change.text
    approved = client.post(f"/plans/{plan_id}/changes/{change.json()['id']}/approve", headers=pm)
    assert approved.status_code == 200, approved.text
    assert sync_query("SELECT count(*) FROM vms.plan_change WHERE work_plan_id = %s AND status <> 'PENDING_PM'",
                      (plan_id,)) == [(1,)]


@W2
def test_incident_and_daily_report_on_running_plan(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    leader = world.headers(client, "leader")

    incident = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "occurred_on": jakarta_now().date().isoformat(), "category": "K3_RINGAN",
        "severity": "RENDAH", "description": "Tangga licin di area kerja", "evidence_file_ids": []})
    assert incident.status_code == 201, incident.text
    resolved = client.post(f"/hse/incidents/{incident.json()['id']}/resolve", headers=world.headers(client, "pm"),
                           json={"resolution_note": "Dipasang karpet anti selip"})
    assert resolved.status_code == 200, resolved.text

    report = client.post(f"/hse/daily-reports/{day_ids[0]}", headers=leader,
                         json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada", "evidence_file_ids": []})
    assert report.status_code == 200, report.text
    submitted = client.post(f"/hse/daily-reports/{day_ids[0]}/submit", headers=leader)
    assert submitted.status_code == 200, submitted.text
    assert sync_query("SELECT status::text FROM vms.daily_report WHERE work_plan_day_id = %s", (day_ids[0],)) \
        == [("SUBMITTED",)]
