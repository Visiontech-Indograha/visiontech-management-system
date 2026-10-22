"""
Milestone 5 · Jadwal harian daily-first (docs/35 §3): minggu = rentang tanggal; DRAFT → SUBMITTED → APPROVED →
ONGOING → COMPLETED; satu jadwal per tim per tanggal; lapangan hanya melihat yang sudah disetujui.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = requires_db


def _body(world: World, days: int = 1, **over):
    return {"division_id": world.unit_id, "team_id": world.team_id,
            "work_date": str(jakarta_now().date() + timedelta(days=days)), "site_name": "Gardu Induk Uji",
            "site_lat": "1.4700000", "site_lng": "101.4500000", **over}


def _create(client, world: World, who: str = "pm", **over):
    return client.post("/work-plans/daily", headers=world.headers(client, who), json=_body(world, **over))


def test_pm_creates_draft_and_runs_full_cycle(client, world: World):
    created = _create(client, world, days=0)
    assert created.status_code == 201, created.text
    plan = created.json()
    assert plan["status"] == "DRAFT" and plan["team_name"]
    pid = plan["daily_plan_id"]
    pm, leader = world.headers(client, "pm"), world.headers(client, "leader")

    assert client.post(f"/work-plans/daily/{pid}/submit", headers=pm).json()["status"] == "SUBMITTED"
    assert client.post(f"/work-plans/daily/{pid}/approve", headers=pm).json()["status"] == "APPROVED"
    assert client.post(f"/work-plans/daily/{pid}/start", headers=pm).status_code == 403  # bukan ketua
    assert client.post(f"/work-plans/daily/{pid}/start", headers=leader).json()["status"] == "ONGOING"
    assert client.post(f"/work-plans/daily/{pid}/complete", headers=leader).json()["status"] == "COMPLETED"


def test_one_plan_per_team_per_day_and_no_past_dates(client, world: World):
    assert _create(client, world).status_code == 201
    taken = _create(client, world)
    assert taken.status_code == 409 and taken.json()["error"]["code"] == "TEAM_DAY_TAKEN"
    assert _create(client, world, days=-1).status_code == 422


def test_team_must_belong_to_division(client, world: World):
    other_division = world.add_unit("Lain")
    assert _create(client, world, division_id=other_division).status_code == 422


def test_pm_of_other_division_cannot_manage(client, world: World, other_world: World):
    assert _create(client, world, who="pm").status_code == 201
    outsider = client.post("/work-plans/daily", headers=other_world.headers(client, "pm"), json=_body(world, days=2))
    assert outsider.status_code == 403


def test_field_staff_only_see_released_plans(client, world: World):
    draft = make_daily_plan(world, status="DRAFT", days_from_today=3)
    approved = make_daily_plan(world, status="APPROVED", days_from_today=4)
    member = world.headers(client, "member")
    assert client.get(f"/work-plans/daily/{draft}", headers=member).status_code == 404
    assert client.get(f"/work-plans/daily/{approved}", headers=member).status_code == 200
    start = str(jakarta_now().date())
    end = str(jakarta_now().date() + timedelta(days=7))
    listed = client.get("/work-plans/daily", headers=member, params={"start": start, "end": end}).json()
    assert [p["daily_plan_id"] for p in listed] == [approved]


def test_reject_returns_to_draft_with_reason(client, world: World):
    pid = make_daily_plan(world, status="SUBMITTED", days_from_today=1)
    rejected = client.post(f"/work-plans/daily/{pid}/reject", headers=world.headers(client, "pm"),
                           json={"reason": "Titik survei kurang"})
    assert rejected.json()["status"] == "DRAFT"
    assert rejected.json()["rejection_reason"] == "Titik survei kurang"


def test_bulk_approve_skips_ineligible(client, world: World, other_world: World):
    mine = make_daily_plan(world, status="SUBMITTED", days_from_today=1)
    done = make_daily_plan(world, status="COMPLETED", days_from_today=2)
    foreign = make_daily_plan(other_world, status="SUBMITTED", days_from_today=1)
    result = client.post("/work-plans/daily/approve", headers=world.headers(client, "pm"),
                         json={"daily_plan_ids": [mine, done, foreign]}).json()
    assert result["approved"] == [mine]
    assert sorted(result["skipped"]) == sorted([done, foreign])


def test_copy_to_other_dates(client, world: World):
    pid = make_daily_plan(world, status="APPROVED", days_from_today=1)
    dates = [str(jakarta_now().date() + timedelta(days=d)) for d in (8, 9)]
    copied = client.post(f"/work-plans/daily/{pid}/copy", headers=world.headers(client, "pm"),
                         json={"work_dates": dates})
    assert copied.status_code == 201, copied.text
    assert {c["status"] for c in copied.json()} == {"DRAFT"}


def test_only_unused_unapproved_plans_can_be_deleted(client, world: World):
    pm = world.headers(client, "pm")
    approved = make_daily_plan(world, status="APPROVED", days_from_today=1)
    assert client.delete(f"/work-plans/daily/{approved}", headers=pm).status_code == 409
    draft = make_daily_plan(world, status="DRAFT", days_from_today=2)
    assert client.delete(f"/work-plans/daily/{draft}", headers=pm).status_code == 200
    assert sync_query("SELECT delete_at IS NOT NULL FROM work_plan_daily WHERE daily_plan_id = %s", (draft,))[0][0]


def test_edit_only_while_draft_or_submitted(client, world: World):
    pm = world.headers(client, "pm")
    draft = make_daily_plan(world, status="DRAFT", days_from_today=1)
    edited = client.put(f"/work-plans/daily/{draft}", headers=pm,
                        json={"site_name": "Site baru", "clock_in_time": "08:00"})
    assert edited.json()["site_name"] == "Site baru"
    bad_hours = client.put(f"/work-plans/daily/{draft}", headers=pm, json={"clock_out_time": "06:00"})
    assert bad_hours.status_code == 422
    approved = make_daily_plan(world, status="APPROVED", days_from_today=2)
    assert client.put(f"/work-plans/daily/{approved}", headers=pm, json={"site_name": "X Site"}).status_code == 409
