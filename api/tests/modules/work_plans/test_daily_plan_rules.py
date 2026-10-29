"""
A8 · Aturan jadwal harian (lanjutan Milestone 5/6): jadwal kosong tidak diajukan/disetujui (PLAN_EMPTY), jadwal
tidak ditutup selagi ada pekerjaan menunggu pemindahan hari (ROLLOVER_PENDING), ketua harus absen masuk sebelum
jadwal dimulai (CHECKIN_REQUIRED), dan salinan jadwal membawa item (progres direset, survei & ketergantungan
dilewati).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item, check_in, make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def test_submit_refuses_empty_plan_then_accepts_it_with_an_item(client, world: World):
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)
    pm = world.headers(client, "pm")

    empty = client.post(f"/work-plans/daily/{plan}/submit", headers=pm)
    assert empty.status_code == 422, empty.text
    assert "PLAN_EMPTY" in empty.text

    add_item(plan, world, "Titik CCTV uji")
    assert client.post(f"/work-plans/daily/{plan}/submit", headers=pm).json()["status"] == "SUBMITTED"


def test_approve_refuses_empty_plan(client, world: World):
    plan = make_daily_plan(world, status="SUBMITTED", days_from_today=1)
    pm = world.headers(client, "pm")

    refused = client.post(f"/work-plans/daily/{plan}/approve", headers=pm)
    assert refused.status_code == 422, refused.text
    assert "PLAN_EMPTY" in refused.text

    add_item(plan, world, "Titik CCTV uji")
    assert client.post(f"/work-plans/daily/{plan}/approve", headers=pm).json()["status"] == "APPROVED"


def test_complete_refused_while_rollover_is_pending(client, world: World):
    plan = make_daily_plan(world, status="ONGOING")
    add_item(plan, world, "Titik menunggu", status="PENDING_ROLLOVER")

    refused = client.post(f"/work-plans/daily/{plan}/complete", headers=world.headers(client, "leader"))
    assert refused.status_code == 409, refused.text
    assert "ROLLOVER_PENDING" in refused.text


def test_start_requires_leader_check_in_for_that_day(client, world: World):
    plan = make_daily_plan(world, status="APPROVED", days_from_today=0)
    add_item(plan, world, "Titik CCTV uji")
    leader = world.headers(client, "leader")

    refused = client.post(f"/work-plans/daily/{plan}/start", headers=leader)
    assert refused.status_code == 409, refused.text
    assert "CHECKIN_REQUIRED" in refused.text

    check_in(client, world, "leader")
    started = client.post(f"/work-plans/daily/{plan}/start", headers=leader)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "ONGOING"


def test_copy_carries_items_with_progress_reset_and_skips_survey_and_dependent(client, world: World):
    plan = make_daily_plan(world, status="APPROVED", days_from_today=1)
    add_item(plan, world, "Instalasi A", status="DONE", completed_qty=4, progress_percent=100)
    add_item(plan, world, "Survei titik", task_phase="SURVEY", is_main_deliverable=False)
    prerequisite = add_item(plan, world, "Pemasangan bergantung", depends_on_item_id=None)
    sync_query("UPDATE work_plan_item SET depends_on_item_id = %s WHERE item_id = %s",
               (prerequisite, add_item(plan, world, "Lanjutan bergantung")))
    target_date = str(jakarta_now().date() + timedelta(days=8))

    copied = client.post(f"/work-plans/daily/{plan}/copy", headers=world.headers(client, "pm"),
                         json={"work_dates": [target_date]})
    assert copied.status_code == 201, copied.text
    new_plan = copied.json()[0]["daily_plan_id"]

    rows = sync_query(
        "SELECT title, status, completed_qty::float, progress_percent::float FROM work_plan_item "
        "WHERE daily_plan_id = %s AND delete_at IS NULL ORDER BY title",
        (new_plan,))
    assert sorted(r[0] for r in rows) == ["Instalasi A", "Pemasangan bergantung"]
    assert all(r[1] == "TODO" and r[2] == 0 and r[3] == 0 for r in rows)
