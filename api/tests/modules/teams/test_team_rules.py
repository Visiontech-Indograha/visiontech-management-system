"""
Milestone 3 · Tim lapangan & anggota (team N─1 office/division/leader, team 1─N member).
Ketua wajib Team Leader dan selalu anggota; PM hanya mengelola tim di divisinya; tim yang dipakai
jadwal harian tidak bisa dihapus.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _create(client, world: World, who: str = "pm", **overrides):
    body = {"office_id": world.org_id, "division_id": world.unit_id,
            "leader_employee_id": world.employees["leader"], "name": f"Tim baru {world.tag}", **overrides}
    return client.post("/teams", headers=world.headers(client, who), json=body)


def test_pm_creates_team_and_leader_becomes_member(client, world: World):
    created = _create(client, world)
    assert created.status_code == 201, created.text
    team_id = created.json()["team_id"]
    detail = client.get(f"/teams/{team_id}", headers=world.headers(client, "pm")).json()
    assert [m["employee_id"] for m in detail["members"]] == [world.employees["leader"]]
    assert detail["member_count"] == 1


@pytest.mark.parametrize("leader", ["member", "pm"])
def test_leader_must_be_team_leader(client, world: World, leader: str):
    response = _create(client, world, leader_employee_id=world.employees[leader])
    assert response.status_code == 422, response.text


def test_team_name_is_unique_per_division(client, world: World):
    assert _create(client, world, name="Tim Kembar").status_code == 201
    duplicate = _create(client, world, name="tim kembar")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "TEAM_NAME_TAKEN"


def test_pm_of_other_division_cannot_see_or_manage(client, world: World, other_world: World):
    outsider = other_world.headers(client, "pm")
    assert client.get(f"/teams/{world.team_id}", headers=outsider).status_code == 404
    assert world.team_id not in [t["team_id"] for t in client.get("/teams", headers=outsider).json()]
    body = {"office_id": world.org_id, "division_id": world.unit_id,
            "leader_employee_id": world.employees["leader"], "name": "Tim penyusup"}
    assert client.post("/teams", headers=outsider, json=body).status_code == 403


def test_field_staff_cannot_manage_teams(client, world: World):
    assert _create(client, world, who="leader").status_code == 403


def test_members_are_field_staff_and_unique(client, world: World):
    pm = world.headers(client, "pm")
    url = f"/teams/{world.team_id}/members"
    assert client.post(url, headers=pm, json={"employee_id": world.employees["hr"]}).status_code == 422
    duplicate = client.post(url, headers=pm, json={"employee_id": world.employees["member"]})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "MEMBER_EXISTS"


def test_member_leaves_and_rejoins_without_duplicate_rows(client, world: World):
    pm = world.headers(client, "pm")
    member = world.employees["member"]
    assert client.delete(f"/teams/{world.team_id}/members/{member}", headers=pm).status_code == 200
    assert client.post(f"/teams/{world.team_id}/members", headers=pm, json={"employee_id": member}).status_code == 201
    rows = sync_query("SELECT count(*) FROM member WHERE team_id = %s AND employee_id = %s", (world.team_id, member))
    assert rows[0][0] == 1


def test_leader_cannot_be_removed(client, world: World):
    response = client.delete(f"/teams/{world.team_id}/members/{world.employees['leader']}",
                             headers=world.headers(client, "pm"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LEADER_REQUIRED"


def test_team_used_by_daily_plan_cannot_be_deleted(client, world: World):
    sync_query(
        "INSERT INTO work_plan_daily (work_date, site_name, site_lat, site_lng, division_id, team_id, created_by_id) "
        "VALUES (CURRENT_DATE, 'Site uji', -6.2, 106.8, %s, %s, %s) RETURNING daily_plan_id",
        (world.unit_id, world.team_id, world.employees["pm"]))
    response = client.delete(f"/teams/{world.team_id}", headers=world.headers(client, "pm"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TEAM_IN_USE"


def test_unused_team_is_archived_with_its_members(client, world: World):
    team_id = _create(client, world).json()["team_id"]
    assert client.delete(f"/teams/{team_id}", headers=world.headers(client, "pm")).status_code == 200
    assert sync_query("SELECT count(*) FROM member WHERE team_id = %s AND delete_at IS NULL", (team_id,))[0][0] == 0
    assert client.get(f"/teams/{team_id}", headers=world.headers(client, "pm")).status_code == 404
