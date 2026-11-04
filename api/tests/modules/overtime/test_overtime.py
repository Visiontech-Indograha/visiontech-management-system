"""
Lembur daily-first (Milestone 5): overtime N─1 work_plan_daily.

  - REPORT: hanya jadwal ONGOING; 0 < jam ≤ 12; alasan wajib; hanya ketua/anggota tim jadwal; tanggal = tanggal
    jadwal; satu pengajuan non-REJECTED per karyawan per jadwal.
  - REVIEW: hanya PENDING_PM; hanya PM/OM divisi jadwal; pengaju ≠ peninjau; APPROVED / REJECTED.
  - LIST: siapa pun yang melihat jadwal. RECAP: OM/admin seluruhnya, PM divisinya; hanya jam APPROVED.
  - Jadwal organisasi/divisi lain → 404.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan, run_daily_to_ongoing

pytestmark = requires_db


def _report(client, world: World, plan_id: str, who: str, hours: float = 2.0,
            reason: str = "Pengerjaan kabel tambahan"):
    return client.post("/overtime", headers=world.headers(client, who),
                       json={"daily_plan_id": plan_id, "hours": hours, "reason": reason})


def _review(client, world: World, ot_id: str, who: str, decision: str = "APPROVED", note: str | None = None):
    return client.post(f"/overtime/{ot_id}/review", headers=world.headers(client, who),
                       json={"decision": decision, "note": note})


def _status(ot_id: str) -> str:
    return sync_query("SELECT status FROM overtime WHERE overtime_id = %s", (ot_id,))[0][0]


@pytest.mark.parametrize("who", ["leader", "member"])
def test_team_reports_overtime_on_ongoing_plan(client, world: World, who: str):
    plan_id = run_daily_to_ongoing(world)
    response = _report(client, world, plan_id, who)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING_PM" and body["daily_plan_id"] == plan_id
    assert body["employee_id"] == world.employees[who]


def test_report_requires_ongoing_plan(client, world: World):
    approved = make_daily_plan(world, status="APPROVED", days_from_today=1)
    assert _report(client, world, approved, "leader").status_code == 409


@pytest.mark.parametrize(("hours", "reason"), [(0, "x alasan"), (12.5, "x alasan"), (2, "   ")])
def test_report_validation(client, world: World, hours: float, reason: str):
    assert _report(client, world, run_daily_to_ongoing(world), "leader", hours, reason).status_code == 422


def test_only_team_reports_and_foreign_plan_is_hidden(client, world: World, other_world: World):
    plan_id = run_daily_to_ongoing(world)
    # HR bukan anggota tim dan tak lagi melihat rencana kerja → 404 (dulu 403); keduanya menolak.
    assert _report(client, world, plan_id, "hr").status_code in (403, 404)
    assert client.post("/overtime", headers=other_world.headers(client, "member"),
                       json={"daily_plan_id": plan_id, "hours": 1, "reason": "x alasan"}).status_code == 404


def test_duplicate_report_rejected(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    assert _report(client, world, plan_id, "member").status_code == 201
    assert _report(client, world, plan_id, "member").status_code == 409


def test_pm_reviews_and_cannot_review_twice(client, world: World):
    ot_id = _report(client, world, run_daily_to_ongoing(world), "member").json()["id"]
    assert _review(client, world, ot_id, "pm").json()["status"] == "APPROVED"
    assert _review(client, world, ot_id, "pm", "REJECTED").status_code == 409


def test_review_rules(client, world: World, other_world: World):
    ot_id = _report(client, world, run_daily_to_ongoing(world), "member").json()["id"]
    assert _review(client, world, ot_id, "leader").status_code == 403          # bukan PM/OM divisi
    assert _review(client, world, ot_id, "pm", "MAYBE").status_code == 422
    assert client.post(f"/overtime/{ot_id}/review", headers=other_world.headers(client, "pm"),
                       json={"decision": "APPROVED"}).status_code == 404       # divisi/organisasi lain
    assert _status(ot_id) == "PENDING_PM"


def test_list_follows_plan_visibility(client, world: World, other_world: World):
    plan_id = run_daily_to_ongoing(world)
    _report(client, world, plan_id, "member")
    listed = client.get("/overtime", headers=world.headers(client, "pm"), params={"daily_plan_id": plan_id})
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert client.get("/overtime", headers=other_world.headers(client, "pm"),
                      params={"daily_plan_id": plan_id}).status_code == 404


def test_recap_counts_only_approved_hours(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    approved = _report(client, world, plan_id, "member", hours=3).json()["id"]
    _report(client, world, plan_id, "leader", hours=5)
    _review(client, world, approved, "pm")
    rows = client.get("/recaps/overtime", headers=world.headers(client, "pm")).json()
    mine = {r["employee_id"]: r for r in rows}
    assert mine[world.employees["member"]]["approved_hours"] == 3
    assert mine[world.employees["leader"]]["approved_hours"] == 0
    assert mine[world.employees["leader"]]["pending_entries"] == 1
    assert client.get("/recaps/overtime", headers=world.headers(client, "member")).status_code == 403


def _flags(client, world: World, who: str, plan_id: str) -> dict[str, bool]:
    rows = client.get("/overtime", headers=world.headers(client, who), params={"daily_plan_id": plan_id}).json()
    return {r["id"]: r["can_review"] for r in rows}


def test_list_flags_only_roles_that_may_review(client, world: World):
    """`can_review` = aturan review: pending, bukan pengaju, dan PM/OM divisi jadwal atau admin."""
    plan_id = run_daily_to_ongoing(world)
    ot_id = _report(client, world, plan_id, "member").json()["id"]
    assert _flags(client, world, "pm", plan_id) == {ot_id: True}
    assert _flags(client, world, "ops", plan_id) == {ot_id: True}
    assert _flags(client, world, "admin", plan_id) == {ot_id: True}
    assert _flags(client, world, "leader", plan_id) == {ot_id: False}
    assert _flags(client, world, "member", plan_id) == {ot_id: False}
    assert _flags(client, world, "hr", plan_id) == {ot_id: False}


def test_flag_matches_review_permission(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    ot_id = _report(client, world, plan_id, "member").json()["id"]
    assert _flags(client, world, "leader", plan_id)[ot_id] is False
    assert _review(client, world, ot_id, "leader").status_code == 403
    assert _flags(client, world, "pm", plan_id)[ot_id] is True
    assert _review(client, world, ot_id, "pm", "REJECTED", "Tidak ada perintah lembur").status_code == 200


def test_flag_off_once_decided(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    ot_id = _report(client, world, plan_id, "member").json()["id"]
    assert _review(client, world, ot_id, "pm").status_code == 200
    assert _flags(client, world, "pm", plan_id) == {ot_id: False}
    assert _flags(client, world, "admin", plan_id) == {ot_id: False}


def test_reported_row_is_not_reviewable_by_its_own_reporter(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    ot_id = _report(client, world, plan_id, "member").json()["id"]
    rows = client.get("/overtime", headers=world.headers(client, "member"), params={"daily_plan_id": plan_id}).json()
    assert [r["id"] for r in rows] == [ot_id] and rows[0]["can_review"] is False
