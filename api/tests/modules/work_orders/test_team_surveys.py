"""
GET /work-orders/team-surveys: survei WO aktif milik tim pemanggil (HP ketua/anggota).
Lintas modul: assign-survey (PM) -> team-surveys (ketua & anggota terlihat; lainnya tidak) -> submit/selesai (hilang).
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = requires_db

URL = "/work-orders/team-surveys"
SURVEY_BODY = {"narrative": "Survei uji", "format": "CCTV", "points": [], "general_bom": []}


def _new_wo(world: World, title: str = "WO survei") -> str:
    tag = uuid.uuid4().hex[:8]
    return str(sync_query(
        "INSERT INTO client_work_orders (wo_number, client_id, division_id, pm_id, title, status) "
        "VALUES (%s, %s, %s, %s, %s, 'WAITING_SURVEY') RETURNING work_order_id",
        (f"TS-{tag}", make_client(), world.unit_id, world.employees["pm"], f"{title} {tag}"))[0][0])


def _assign(client, world: World, wo_id: str, who: str = "pm", **over):
    body = {"lead_team_id": world.team_id, "survey_date": "2026-12-01", **over}
    return client.post(f"/work-orders/{wo_id}/assign-survey", headers=world.headers(client, who), json=body)


def _ids(client, world: World, who: str, query: str = "") -> list[str]:
    res = client.get(URL + query, headers=world.headers(client, who))
    assert res.status_code == 200, (who, res.text)
    return [r["work_order_id"] for r in res.json()]


def _other_team(world: World) -> None:
    """Tim lain di kantor yang sama; ketuanya `rival`."""
    rival = world.add_person("rival", None)
    team2 = sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, world.unit_id, rival, "Tim lain"))[0][0]
    sync_query("INSERT INTO member (team_id, employee_id) VALUES (%s, %s)", (team2, rival))


def test_assign_requires_date_and_returns_summary(client, world: World):
    wo = _new_wo(world)
    missing = client.post(f"/work-orders/{wo}/assign-survey", headers=world.headers(client, "pm"),
                          json={"lead_team_id": world.team_id})
    assert missing.status_code == 422, missing.text
    assert "Tanggal survei wajib" in missing.json()["error"]["message"]
    ok = _assign(client, world, wo)
    assert ok.status_code == 200, ok.text
    summary = ok.json()["survey_assignment_summary"]
    assert "akan melihat di HP pada tanggal 01-12-2026" in summary and summary.startswith("Tim Tim uji")


def test_leader_and_member_see_assigned_survey_others_do_not(client, world: World):
    _other_team(world)
    world.add_person("outsider", None)
    wo = _new_wo(world)
    assert _ids(client, world, "leader") == []
    assert _assign(client, world, wo).status_code == 200
    for who in ("leader", "member"):
        rows = client.get(URL, headers=world.headers(client, who)).json()
        assert [r["work_order_id"] for r in rows] == [wo], who
        row = rows[0]
        assert row["survey_date"] == "2026-12-01" and row["survey_status"] == "DRAFT"
        assert row["filled_points"] == 0 and row["surveyor_team_id"] == world.team_id
        assert {"survey_id", "wo_number", "title", "client_name", "site_name", "site_lat", "site_lng",
                "site_radius_m", "surveyor_team_name"} <= set(row)
    for who in ("rival", "outsider", "pm", "ops", "admin", "hr"):
        assert wo not in _ids(client, world, who), who


def test_submitted_or_completed_survey_disappears(client, world: World):
    wo_a, wo_b = _new_wo(world, "A"), _new_wo(world, "B")
    for wo in (wo_a, wo_b):
        assert _assign(client, world, wo).status_code == 200
    assert set(_ids(client, world, "member")) == {wo_a, wo_b}
    sent = client.post(f"/work-orders/{wo_a}/submit-survey", headers=world.headers(client, "member"),
                       json=SURVEY_BODY)
    assert sent.status_code == 200, sent.text
    assert _ids(client, world, "member") == [wo_b]
    sync_query("UPDATE client_work_orders SET status = 'COMPLETED' WHERE work_order_id = %s", (wo_b,))
    assert _ids(client, world, "leader") == []


def test_paging_and_prefix_search(client, world: World):
    wo_a, wo_b = _new_wo(world, "Alfa"), _new_wo(world, "Bravo")
    for wo in (wo_a, wo_b):
        assert _assign(client, world, wo).status_code == 200
    res = client.get(URL + "?size=1", headers=world.headers(client, "leader"))
    assert res.status_code == 200 and len(res.json()) == 1 and res.headers["X-Total-Count"] == "2"
    assert _ids(client, world, "leader", "?q=Bravo") == [wo_b]
    assert _ids(client, world, "leader", "?q=ravo") == []


def test_reassign_moves_draft_to_new_team_and_date(client, world: World):
    _other_team(world)
    wo = _new_wo(world)
    assert _assign(client, world, wo).status_code == 200
    team2 = sync_query("SELECT team_id FROM team WHERE name = 'Tim lain' AND office_id = %s", (world.org_id,))[0][0]
    assert _assign(client, world, wo, lead_team_id=str(team2), survey_date="2026-12-05").status_code == 200
    assert _ids(client, world, "leader") == []
    assert _ids(client, world, "rival") == [wo]
