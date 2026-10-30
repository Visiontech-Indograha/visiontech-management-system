"""
Milestone 6 · Item per titik, prasyarat, progres & rollover (docs/35 §3–4, keputusan pemilik 2026-10-20).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = requires_db


def _work_type(world: World, name: str = "Instalasi CCTV uji", mandatory_photo: bool = False) -> str:
    wt = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                        (world.unit_id, f"{name} {world.tag}"))[0][0])
    if mandatory_photo:
        sync_query("INSERT INTO image_requirement (work_type_id, name, path_image, is_mandatory, sort_order) "
                   "VALUES (%s, 'Foto sesudah', 'sop/x.png', TRUE, 1)", (wt,))
    return wt


def _survey_work_type(world: World) -> str:
    wt = _work_type(world, name="Survei CCTV uji")
    sync_query("UPDATE work_type SET kind = 'SURVEY_TASK' WHERE work_type_id = %s", (wt,))
    return wt


def _item(client, world: World, plan_id: str, wt: str, who: str = "pm", **over):
    body = {"work_type_id": wt, "title": "Titik CCTV 1", "task_phase": "INSTALLATION", "is_main_deliverable": True,
            "target_qty": "4", **over}
    return client.post(f"/work-plans/daily/{plan_id}/items", headers=world.headers(client, who), json=body)


def _start(plan_id: str) -> None:
    sync_query("UPDATE work_plan_daily SET status = 'ONGOING' WHERE daily_plan_id = %s", (plan_id,))


def test_pm_adds_items_only_while_editable(client, world: World):
    wt = _work_type(world)
    draft = make_daily_plan(world, status="DRAFT", days_from_today=1)
    created = _item(client, world, draft, wt, notes="Tiang 6 m, butuh bracket")
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "TODO" and created.json()["notes"] == "Tiang 6 m, butuh bracket"
    approved = make_daily_plan(world, status="APPROVED", days_from_today=2)
    assert _item(client, world, approved, wt).status_code == 409
    assert _item(client, world, draft, wt, who="leader").status_code == 403


def test_template_must_belong_to_plan_division(client, world: World):
    other = world.add_unit("Lain")
    # PM dunia uji juga PM divisi "Lain" (multi-divisi boleh memakai template di sana); di sini divisi itu
    # dipimpin orang lain, sehingga template-nya bukan milik PM ini.
    stranger = world.add_person(f"pm_lain_{world.tag}", "PM")
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (stranger, other))
    foreign_wt = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, 'Survei lain') "
                                "RETURNING work_type_id", (other,))[0][0])
    draft = make_daily_plan(world, status="DRAFT", days_from_today=1)
    assert _item(client, world, draft, foreign_wt).status_code == 422


@pytest.mark.parametrize("phase", ["SURVEY", "PREPARATION"])
def test_only_main_phases_can_be_main_deliverable(client, world: World, phase: str):
    draft = make_daily_plan(world, status="DRAFT", days_from_today=1)
    assert _item(client, world, draft, _work_type(world), task_phase=phase).status_code == 422


def test_assignment_only_for_team_members(client, world: World):
    draft = make_daily_plan(world, status="DRAFT", days_from_today=1)
    wt = _work_type(world)
    assert _item(client, world, draft, wt, assigned_employee_ids=[world.employees["hr"]]).status_code == 422
    assert _item(client, world, draft, wt, assigned_employee_ids=[world.employees["member"]]).status_code == 201


def test_survey_phase_only_on_survey_template(client, world: World):
    """Fase SURVEY eksplisit ditolak pada template pekerjaan biasa (WORK), diterima pada template survei."""
    plan = make_daily_plan(world, status="DRAFT", days_from_today=0)
    rejected = _item(client, world, plan, _work_type(world), task_phase="SURVEY", is_main_deliverable=False)
    assert rejected.status_code == 422, rejected.text
    accepted = _item(client, world, plan, _survey_work_type(world), task_phase="SURVEY",
                     is_main_deliverable=False)
    assert accepted.status_code == 201, accepted.text


def test_prerequisite_blocks_progress_until_done(client, world: World):
    plan = make_daily_plan(world, status="DRAFT", days_from_today=0)
    wt = _work_type(world)
    survey = _item(client, world, plan, _survey_work_type(world), title="Survei titik 1", task_phase="SURVEY",
                   is_main_deliverable=False, target_qty="1").json()["item_id"]
    main = _item(client, world, plan, wt, depends_on_item_id=survey).json()["item_id"]
    _start(plan)
    member = world.headers(client, "member")
    blocked = client.patch(f"/work-plans/items/{main}/progress", headers=member, json={"completed_qty": "1"})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "PREREQUISITE_NOT_DONE"
    assert client.patch(f"/work-plans/items/{survey}/progress", headers=member,
                        json={"completed_qty": "1"}).json()["status"] == "DONE"
    assert client.patch(f"/work-plans/items/{main}/progress", headers=member,
                        json={"completed_qty": "2"}).json()["status"] == "IN_PROGRESS"
    assert client.patch(f"/work-plans/items/{main}/progress", headers=member,
                        json={"completed_qty": "9"}).status_code == 422          # melebihi target


def test_done_requires_mandatory_photos(client, world: World, fake_storage):
    import io

    from PIL import Image

    plan = make_daily_plan(world, status="DRAFT", days_from_today=0)
    wt = _work_type(world, mandatory_photo=True)
    item = _item(client, world, plan, wt, target_qty="1").json()["item_id"]
    _start(plan)
    member = world.headers(client, "member")
    missing = client.patch(f"/work-plans/items/{item}/progress", headers=member, json={"completed_qty": "1"})
    assert missing.status_code == 422 and missing.json()["error"]["code"] == "PHOTOS_REQUIRED"

    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(buf, "PNG")
    file_id = client.post("/files/upload", headers=member,
                          files={"file": ("f.png", buf.getvalue(), "image/png")}).json()["file_id"]
    req_id = str(sync_query("SELECT image_requirement_id FROM image_requirement WHERE work_type_id = %s", (wt,))[0][0])
    done = client.patch(f"/work-plans/items/{item}/progress", headers=member,
                        json={"completed_qty": "1", "photos": [{"file_id": file_id, "requirement_id": req_id}]})
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "DONE"


def _pending_rollover(client, world: World) -> tuple[str, str]:
    plan = make_daily_plan(world, status="DRAFT", days_from_today=0)
    item = _item(client, world, plan, _work_type(world), target_qty="10").json()["item_id"]
    _start(plan)
    requested = client.post(f"/work-plans/items/{item}/request-rollover", headers=world.headers(client, "leader"),
                            json={"delay_reason": "Hujan deras", "completed_qty": "6"})
    assert requested.status_code == 200, requested.text
    assert requested.json()["rollover_approval_status"] == "WAITING_PM"
    return plan, item


def test_only_leader_requests_rollover(client, world: World):
    plan = make_daily_plan(world, status="DRAFT", days_from_today=0)
    item = _item(client, world, plan, _work_type(world)).json()["item_id"]
    _start(plan)
    assert client.post(f"/work-plans/items/{item}/request-rollover", headers=world.headers(client, "member"),
                       json={"delay_reason": "Hujan", "completed_qty": "1"}).status_code == 403


def test_rollover_to_new_date_creates_day_and_carries_remaining_volume(client, world: World):
    _, item = _pending_rollover(client, world)
    target = str(jakarta_now().date() + timedelta(days=3))
    decided = client.post(f"/work-plans/items/{item}/rollover-decision", headers=world.headers(client, "pm"),
                          json={"approve": True, "target_date": target, "note": "Lanjut Kamis"})
    assert decided.status_code == 200, decided.text
    new = decided.json()
    assert new["origin_item_id"] == item and float(new["target_qty"]) == 4 and new["work_date"] == target
    origin = sync_query("SELECT status, delay_reason, shifted_to_daily_id::text FROM work_plan_item "
                        "WHERE item_id = %s", (item,))[0]
    assert origin == ("SHIFTED_DAY", "Hujan deras", new["daily_plan_id"])          # alasan ketua tidak ditimpa
    assert sync_query("SELECT count(*) FROM app_activity_logs WHERE entity_id = %s AND action = 'ROLLOVER_DECIDED'",
                      (item,))[0][0] == 1
    chain = client.get(f"/work-plans/items/{new['item_id']}/chain", headers=world.headers(client, "pm")).json()
    assert [c["item_id"] for c in chain] == [item, new["item_id"]]


def test_rollover_rules(client, world: World):
    _, item = _pending_rollover(client, world)
    pm = world.headers(client, "pm")
    url = f"/work-plans/items/{item}/rollover-decision"
    today = str(jakarta_now().date())
    assert client.post(url, headers=pm, json={"approve": True, "target_date": today}).status_code == 422  # ≤ asal
    other_team = sync_query("INSERT INTO team (office_id, division_id, leader_employee_id, name) "
                            "VALUES (%s, %s, %s, 'Tim lain') RETURNING team_id",
                            (world.org_id, world.unit_id, world.employees["leader"]))[0][0]
    other_day = make_daily_plan(world, status="APPROVED", days_from_today=2, team_id=str(other_team))
    assert client.post(url, headers=pm, json={"approve": True, "target_daily_plan_id": other_day}).status_code == 422
    rejected = client.post(url, headers=pm, json={"approve": False, "note": "Kerjakan hari ini"})
    assert rejected.json()["rollover_approval_status"] == "REJECTED_BY_PM"
    assert client.post(url, headers=pm, json={"approve": False}).status_code == 409   # tidak menunggu lagi


def test_shifted_item_cannot_be_shifted_again(client, world: World):
    _, item = _pending_rollover(client, world)
    target = str(jakarta_now().date() + timedelta(days=4))
    client.post(f"/work-plans/items/{item}/rollover-decision", headers=world.headers(client, "pm"),
                json={"approve": True, "target_date": target})
    again = client.post(f"/work-plans/items/{item}/request-rollover", headers=world.headers(client, "leader"),
                        json={"delay_reason": "Lagi", "completed_qty": "0"})
    assert again.status_code == 409
