"""
V-02 · Alur modul yang bergantung pada SK: aset (M6), siklus SK (M3), insiden (M7), laporan harian (M5).

Alur SK sempat ditandai `xfail(strict=True)` sampai W2 (V-03…V-06) selesai; penandanya dicabut
begitu xfail ketat mendeteksi alurnya lulus (2026-09-24).
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

def _row_version(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def create_draft_plan(client, world: World, start_offset_days: int = 0, length_days: int = 2,
                      leader: str = "leader") -> tuple[str, list[str]]:
    """SK draft lengkap: periode, satu hari kerja per tanggal, masing-masing satu tugas. → (plan_id, day_ids)."""
    start = jakarta_now().date() + timedelta(days=start_offset_days)
    end = start + timedelta(days=length_days - 1)
    pm = world.headers(client, "pm")
    plan = client.post("/work-plans", headers=pm, json={
        "title": "Instalasi CCTV gudang", "unit_id": world.unit_id, "site_id": world.site_id,
        "location_text": "Gudang uji", "period_start": start.isoformat(), "period_end": end.isoformat(),
        "pm_employee_id": world.employees["pm"], "leader_employee_id": world.employees[leader]})
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    day_ids = []
    for i in range(length_days):
        day = client.post(f"/work-plans/{plan_id}/days", headers=pm,
                          json={"work_date": (start + timedelta(days=i)).isoformat(), "title": f"Hari {i + 1}"})
        assert day.status_code == 200, day.text
        day_ids.append(day.json()["id"])
        task = client.post(f"/work-plans/{plan_id}/days/{day_ids[-1]}/tasks", headers=pm, json={"title": "Pasang kamera"})
        assert task.status_code == 200, task.text
    return plan_id, day_ids


def run_plan_to_in_progress(client, world: World, length_days: int = 2) -> tuple[str, list[str]]:
    plan_id, day_ids = run_plan_to_accepted(client, world, length_days)

    # START oleh ketua menurut SK (domain.js: LEADER), bukan PM.
    started = client.post(f"/work-plans/{plan_id}/start", headers=world.headers(client, "leader"),
                          json={"row_version": _row_version(plan_id), "reason": ""})
    assert started.status_code == 200, started.text
    assert sync_query("SELECT status::text FROM vms.work_plan WHERE id = %s", (plan_id,)) == [("IN_PROGRESS",)]
    return plan_id, day_ids


def run_plan_to_accepted(client, world: World, length_days: int = 2,
                         start_offset_days: int = 0) -> tuple[str, list[str]]:
    """SK terbit & diterima ketua. Alur SK v2: bila tanggal mulai sudah tiba (offset 0) SK langsung Berjalan;
    pakai `start_offset_days=1` untuk SK Diterima yang belum berjalan."""
    plan_id, day_ids = create_draft_plan(client, world, start_offset_days, length_days=length_days)
    pm = world.headers(client, "pm")

    members = client.put(f"/work-plans/{plan_id}/members", headers=pm, json={
        "leader_employee_id": world.employees["leader"],
        "member_employee_ids": [world.employees["member"]], "row_version": _row_version(plan_id)})
    assert members.status_code == 200, members.text

    published = client.post(f"/work-plans/{plan_id}/publish", headers=pm, json={"row_version": _row_version(plan_id), "reason": ""})
    assert published.status_code == 200, published.text
    assert sync_query("SELECT kind::text, status::text FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,)) \
        == [("INITIAL_ORDER", "AWAITING_ACCEPTANCE")]

    accepted = client.post(f"/work-plans/{plan_id}/accept", headers=world.headers(client, "leader"),
                           json={"row_version": _row_version(plan_id), "reason": ""})
    assert accepted.status_code == 200, accepted.text
    assert sync_query("SELECT status::text FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,)) == [("EFFECTIVE",)]
    return plan_id, day_ids


def test_plans_created_back_to_back_get_distinct_numbers(client, world: World):
    """Temuan uji nyata R-17: nomor SK memakai 8 karakter AWAL id (UUIDv7 = cap waktu), jadi SK yang
    dibuat berdekatan bernomor sama → terbit gagal 500 (duplicate key). Kini bagian acak id yang dipakai."""
    pm = world.headers(client, "pm")
    numbers = []
    for offset in (20, 25):  # tanggal berbeda: tidak bentrok jadwal ketua/anggota
        plan_id, _ = create_draft_plan(client, world, start_offset_days=offset, length_days=1)
        members = client.put(f"/work-plans/{plan_id}/members", headers=pm, json={
            "leader_employee_id": world.employees["leader"],
            "member_employee_ids": [world.employees["member"]], "row_version": _row_version(plan_id)})
        assert members.status_code == 200, members.text
        published = client.post(f"/work-plans/{plan_id}/publish", headers=pm,
                                json={"row_version": _row_version(plan_id), "reason": ""})
        assert published.status_code == 200, published.text
        numbers.append(published.json()["number"])
    assert numbers[0] != numbers[1]


def test_asset_cycle_reserve_return_verify(client, world):
    # Pengembalian diajukan ketua menurut SK peminjam (V-09); SK draf belum terlihat oleh ketua.
    plan_id, _ = run_plan_to_in_progress(client, world)
    asset_officer = world.headers(client, "asset")

    asset = client.post("/assets", headers=asset_officer,
                        json={"kind": "TOOL", "code": "TL-UJI", "name": "Tangga lipat", "condition": "BAIK"})
    assert asset.status_code == 201, asset.text
    asset_id = asset.json()["id"]

    allocated = client.post(f"/assets/{asset_id}/reserve", headers=asset_officer, json={"work_plan_id": plan_id})
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


def test_plan_lifecycle_to_extension(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    pm = world.headers(client, "pm")

    # Perpanjangan diajukan ketua (REQUEST_CHANGE), disetujui PM (APPROVE_CHANGE).
    change = client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, "leader"),
                         json={"type": "EXTEND", "new_period_end": (jakarta_now().date() + timedelta(days=5)).isoformat(),
                               "reason": "Hujan deras dua hari"})
    assert change.status_code == 201, change.text
    approved = client.post(f"/changes/{change.json()['id']}/approve", headers=pm, json={})
    assert approved.status_code == 200, approved.text
    assert sync_query("SELECT count(*) FROM vms.plan_change WHERE work_plan_id = %s AND status <> 'PENDING_PM'",
                      (plan_id,)) == [(1,)]


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
    # Baca ulang: PM melihat insiden SK beserta statusnya; SK asing → 404.
    listed = client.get("/hse/incidents", params={"plan_id": plan_id}, headers=world.headers(client, "pm"))
    assert listed.status_code == 200, listed.text
    assert [(i["id"], i["status"]) for i in listed.json()] == [(incident.json()["id"], "RESOLVED")]
    assert client.get("/hse/incidents", params={"plan_id": str(uuid.uuid4())},
                      headers=world.headers(client, "pm")).status_code == 404

    report = client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=leader,
                         json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada", "evidence_file_ids": []})
    assert report.status_code == 200, report.text
    submitted = client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/submit", headers=leader)
    assert submitted.status_code == 200, submitted.text
    assert sync_query("SELECT status::text FROM vms.daily_report WHERE work_plan_day_id = %s", (day_ids[0],)) \
        == [("SUBMITTED",)]
