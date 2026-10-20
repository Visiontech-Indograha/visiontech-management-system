"""
V-30 · Lini masa OPS dikelompokkan per pekerjaan + rekap absensi (dok 03 M11, dok 05 §3.13).
- GET /timeline?from=&to= — izin `view:timeline` (PM, OPS, ADMIN). Satu kelompok per SK yang terlihat,
  kecuali CANCELLED/COMPLETED (prototipe operations.js timeline()), urut tanggal mulai. Tiap hari berstatus
  APPROVED | SUBMITTED | CHANGES_REQUESTED | LATE | TODAY | UPCOMING; ringkasan approved_days & late_days.
- GET /recaps/attendance?month=YYYY-MM — FINANCE/HR/OPS/ADMIN: seluruh organisasi; lainnya: hanya dirinya.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.modules.reports.test_weekly_reports import _approve_days
from tests.modules.work_plans.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _timeline(client, world: World, who: str, **params):
    return client.get("/timeline", headers=world.headers(client, who), params=params)


def _group(body: list[dict], plan_id: str) -> dict | None:
    return next((g for g in body if g["id"] == plan_id), None)


def test_timeline_groups_days_per_plan(client, world: World):
    running, days = run_plan_to_in_progress(client, world)
    _approve_days(days[:1])
    world.add_person("other_leader", None)  # R-26: ketua harus staf lapangan, bukan peran kantor
    # Ketua lain: ketua SK berjalan sudah terjadwal di tanggal ini (PERSONNEL_CONFLICT).
    late_draft, _ = create_draft_plan(client, world, start_offset_days=-1, leader="other_leader")
    cancelled, _ = create_draft_plan(client, world, start_offset_days=30, leader="other_leader")
    sync_query("UPDATE vms.work_plan SET status = 'CANCELLED' WHERE id = %s", (cancelled,))
    today = jakarta_now().date()

    response = _timeline(client, world, "ops")
    assert response.status_code == 200, response.text
    body = response.json()

    group = _group(body, running)
    assert group is not None and group["leader"]["employee_id"] == world.employees["leader"]
    assert [(d["work_date"], d["state"]) for d in group["days"]] == [
        (today.isoformat(), "APPROVED"), ((today + timedelta(days=1)).isoformat(), "UPCOMING")]
    assert (group["total_days"], group["approved_days"], group["late_days"]) == (2, 1, 0)

    late = _group(body, late_draft)
    assert late is not None and [d["state"] for d in late["days"]] == ["LATE", "TODAY"]
    assert late["late_days"] == 1
    assert _group(body, cancelled) is None
    starts = [g["period_start"] for g in body]
    assert starts == sorted(starts)


def test_timeline_follows_plan_visibility_and_permission(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world)
    other_unit = world.add_unit("LAIN")
    world.add_person("pm_other", "PM", other_unit, per_unit=True)

    assert _group(_timeline(client, world, "pm").json(), plan_id) is not None
    other = _timeline(client, world, "pm_other")
    assert other.status_code == 200 and _group(other.json(), plan_id) is None
    assert _timeline(client, world, "member").status_code == 403

    later = (jakarta_now().date() + timedelta(days=10)).isoformat()
    outside = _timeline(client, world, "ops", **{"from": later, "to": later})
    assert _group(outside.json(), plan_id) is None


def _attendance(world: World, who: str, status: str) -> None:
    """Trigger attendance_geofence menetapkan status saat INSERT (dari jarak) → status lain disetel sesudahnya."""
    sync_query(
        "WITH ins AS (INSERT INTO vms.attendance (organization_id, employee_id, work_date, site_label, check_in_at, "
        "radius_m) VALUES (%s, %s, %s, 'Gudang uji', now(), 100) RETURNING id) SELECT id FROM ins",
        (world.org_id, world.employees[who], jakarta_now().date()))
    sync_query("UPDATE vms.attendance SET status = %s WHERE employee_id = %s AND work_date = %s",
               (status, world.employees[who], jakarta_now().date()))


def test_attendance_recap_counts_per_employee(client, world: World):
    _attendance(world, "member", "AUTO_VALID")
    _attendance(world, "leader", "NEEDS_REVIEW")
    month = jakarta_now().date().strftime("%Y-%m")

    finance = client.get("/recaps/attendance", headers=world.headers(client, "finance"), params={"month": month})
    assert finance.status_code == 200, finance.text
    rows = {r["employee_id"]: r for r in finance.json()["employees"]}
    assert (rows[world.employees["member"]]["days_present"], rows[world.employees["member"]]["auto_valid"]) == (1, 1)
    assert (rows[world.employees["leader"]]["days_present"], rows[world.employees["leader"]]["needs_review"]) == (0, 1)

    own = client.get("/recaps/attendance", headers=world.headers(client, "member"), params={"month": month})
    assert own.status_code == 200
    assert [r["employee_id"] for r in own.json()["employees"]] == [world.employees["member"]]
    bad = client.get("/recaps/attendance", headers=world.headers(client, "member"), params={"month": "2026-13"})
    assert bad.status_code == 422
