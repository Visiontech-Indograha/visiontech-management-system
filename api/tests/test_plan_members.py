"""
V-05 · Susunan tim SK draft (PUT /work-plans/{id}/members).
Ketua & anggota berasal dari SK (aturan inti #1): baris anggota ditulis dengan rentang terbuka sehingga
`vms.is_plan_leader`/`vms.is_plan_member` langsung mengenalinya. Acuan: domain.js checkMembers/checkSchedule.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan

pytestmark = requires_db


def _rv(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def _user_id(world: World, who: str) -> str:
    return str(sync_query("SELECT id FROM vms.app_user WHERE login = %s", (world.logins[who],))[0][0])


def _put(client, world, plan_id, leader, members, who="pm", row_version=None):
    return client.put(f"/work-plans/{plan_id}/members", headers=world.headers(client, who), json={
        "leader_employee_id": leader, "member_employee_ids": members,
        "row_version": _rv(plan_id) if row_version is None else row_version})


def test_leader_and_members_are_recognised_by_db_authority_functions(client, world):
    plan_id, _ = create_draft_plan(client, world)

    response = _put(client, world, plan_id, world.employees["leader"], [world.employees["member"]])

    assert response.status_code == 200, response.text
    assert response.json()["leader_employee_id"] == world.employees["leader"]
    assert sync_query("SELECT vms.is_plan_leader(%s, %s), vms.is_plan_member(%s, %s)",
                      (plan_id, _user_id(world, "leader"), plan_id, _user_id(world, "member"))) == [(True, True)]
    assert sync_query("SELECT count(*) FROM vms.work_plan_member WHERE work_plan_id = %s AND upper(valid_period) IS NOT NULL",
                      (plan_id,)) == [(0,)]


def test_replacing_the_team_drops_previous_members(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _put(client, world, plan_id, world.employees["leader"], [world.employees["member"]])

    response = _put(client, world, plan_id, world.employees["leader"], [world.employees["finance"]])

    assert response.status_code == 200, response.text
    members = {str(e) for (e,) in sync_query(
        "SELECT employee_id FROM vms.work_plan_member WHERE work_plan_id = %s AND role_in_plan = 'MEMBER'", (plan_id,))}
    assert members == {world.employees["finance"]}


def test_create_plan_with_leader_writes_an_active_leader_row(client, world):
    plan_id, _ = create_draft_plan(client, world)  # POST /plans dengan leader_employee_id

    assert sync_query("SELECT vms.is_plan_leader(%s, %s)", (plan_id, _user_id(world, "leader"))) == [(True,)]


def test_leader_cannot_also_be_member(client, world):
    plan_id, _ = create_draft_plan(client, world)

    response = _put(client, world, plan_id, world.employees["leader"], [world.employees["leader"]])

    assert response.status_code == 422
    assert "Ketua" in response.json()["error"]["message"]


def test_employee_from_another_organisation_is_not_found(client, world, make_user):
    plan_id, _ = create_draft_plan(client, world)
    stranger = str(uuid.uuid4())

    response = _put(client, world, plan_id, world.employees["leader"], [stranger])

    assert response.status_code == 404


def test_stale_row_version_is_rejected(client, world):
    plan_id, _ = create_draft_plan(client, world)

    response = _put(client, world, plan_id, world.employees["leader"], [], row_version=_rv(plan_id) - 1)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_team_is_locked_once_plan_is_not_draft(client, world):
    plan_id, _ = create_draft_plan(client, world)
    sync_query("UPDATE vms.work_plan SET status = 'PUBLISHED' WHERE id = %s", (plan_id,))

    response = _put(client, world, plan_id, world.employees["leader"], [])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PLAN_NOT_DRAFT"


def test_schedule_conflict_is_reported_with_the_other_plan(client, world):
    busy_plan, _ = create_draft_plan(client, world)
    _put(client, world, busy_plan, world.employees["leader"], [world.employees["member"]])
    sync_query("UPDATE vms.work_plan SET status = 'PUBLISHED' WHERE id = %s", (busy_plan,))
    plan_id, _ = create_draft_plan(client, world, leader="ops")  # periode sama, ketua lain

    response = _put(client, world, plan_id, world.employees["ops"], [world.employees["member"]])

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "PERSONNEL_CONFLICT"
    assert {c["work_plan_id"] for c in error["details"]["conflicts"]} == {busy_plan}


def test_only_plan_managers_may_set_the_team(client, world):
    plan_id, _ = create_draft_plan(client, world)

    response = _put(client, world, plan_id, world.employees["leader"], [], who="member")

    # SK draf tidak terlihat oleh anggota (V-07, domain.js visiblePlans) → 404, bukan 403.
    assert response.status_code == 404


def test_team_can_be_read_by_plan_viewers(client, world, other_world):
    """Detail SK menampilkan tim aktif (temuan R-18: web hanya menampilkan ketua)."""
    plan_id, _ = create_draft_plan(client, world)
    assert _put(client, world, plan_id, world.employees["leader"], [world.employees["member"]]).status_code == 200

    team = client.get(f"/work-plans/{plan_id}/members", headers=world.headers(client, "pm"))
    assert team.status_code == 200, team.text
    assert [(m["employee_id"], m["role_in_plan"], m["full_name"]) for m in team.json()] == [
        (world.employees["leader"], "LEADER", "Karyawan uji leader"),
        (world.employees["member"], "MEMBER", "Karyawan uji member"),
    ]
    assert all(m["position"] == "Teknisi" for m in team.json())
    assert client.get(f"/work-plans/{plan_id}/members",
                      headers=other_world.headers(client, "pm")).status_code == 404
