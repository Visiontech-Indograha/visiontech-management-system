"""R-23: pembuat SK dan cakupan personel dijaga server, bukan hanya pilihan UI."""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan

pytestmark = requires_db


def _body(world: World, *, pm: str, unit: str | None = None) -> dict[str, str | None]:
    start = jakarta_now().date() + timedelta(days=20)
    return {
        "title": "Pekerjaan R-23",
        "unit_id": unit or world.unit_id,
        "site_id": world.site_id,
        "location_text": "Gudang uji",
        "description": None,
        "period_start": start.isoformat(),
        "period_end": (start + timedelta(days=1)).isoformat(),
        "pm_employee_id": pm,
        "leader_employee_id": None,
    }


def test_pm_must_be_the_plan_pm(client, world: World):
    response = client.post(
        "/work-plans",
        headers=world.headers(client, "pm"),
        json=_body(world, pm=world.employees["leader"]),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PLAN_PM_MUST_BE_SELF"
    assert sync_query(
        "SELECT count(*) FROM vms.work_plan WHERE organization_id = %s AND title = 'Pekerjaan R-23'",
        (world.org_id,),
    ) == [(0,)]


def test_ops_may_choose_a_pm(client, world: World):
    response = client.post(
        "/work-plans",
        headers=world.headers(client, "ops"),
        json=_body(world, pm=world.employees["pm"]),
    )

    assert response.status_code == 201, response.text
    assert response.json()["pm_employee_id"] == world.employees["pm"]
    assert sync_query(
        "SELECT pm_employee_id::text FROM vms.work_plan WHERE id = %s",
        (response.json()["id"],),
    ) == [(world.employees["pm"],)]


def test_assignment_options_only_include_field_staff(client, world: World):
    start = jakarta_now().date() + timedelta(days=30)
    response = client.get(
        "/work-plans/assignment-options",
        headers=world.headers(client, "ops"),
        params={"period_start": start.isoformat(), "period_end": (start + timedelta(days=1)).isoformat()},
    )

    assert response.status_code == 200, response.text
    candidates = {person["id"] for person in response.json()["personnel_options"]}
    assert {world.employees["leader"], world.employees["member"]} <= candidates
    assert candidates.isdisjoint({
        world.employees[role]
        for role in ("admin", "hr", "pm", "finance", "asset", "ops")
    })


def test_office_roles_cannot_be_submitted_as_leader_or_member(client, world: World):
    create_body = _body(world, pm=world.employees["pm"])
    create_body["leader_employee_id"] = world.employees["ops"]
    rejected_create = client.post(
        "/work-plans",
        headers=world.headers(client, "ops"),
        json=create_body,
    )
    assert rejected_create.status_code == 422
    assert rejected_create.json()["error"]["code"] == "PERSONNEL_NOT_FIELD_STAFF"

    created = client.post(
        "/work-plans",
        headers=world.headers(client, "ops"),
        json=_body(world, pm=world.employees["pm"]),
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]

    office_leader = client.put(
        f"/work-plans/{plan_id}/members",
        headers=world.headers(client, "ops"),
        json={
            "leader_employee_id": world.employees["ops"],
            "member_employee_ids": [world.employees["member"]],
            "row_version": created.json()["row_version"],
        },
    )
    assert office_leader.status_code == 422
    assert office_leader.json()["error"]["code"] == "PERSONNEL_NOT_FIELD_STAFF"

    office_member = client.put(
        f"/work-plans/{plan_id}/members",
        headers=world.headers(client, "ops"),
        json={
            "leader_employee_id": world.employees["leader"],
            "member_employee_ids": [world.employees["hr"]],
            "row_version": created.json()["row_version"],
        },
    )
    assert office_member.status_code == 422
    assert office_member.json()["error"]["code"] == "PERSONNEL_NOT_FIELD_STAFF"


def test_pm_team_is_limited_to_own_unit_but_ops_is_not(client, world: World):
    other_unit = world.add_unit("OTHER_R23")
    outsider = world.add_person("outsider_r23", None, unit_id=other_unit)

    created = client.post(
        "/work-plans",
        headers=world.headers(client, "pm"),
        json=_body(world, pm=world.employees["pm"]),
    )
    assert created.status_code == 201, created.text
    plan_id = created.json()["id"]

    denied = client.put(
        f"/work-plans/{plan_id}/members",
        headers=world.headers(client, "pm"),
        json={
            "leader_employee_id": outsider,
            "member_employee_ids": [world.employees["member"]],
            "row_version": created.json()["row_version"],
        },
    )
    assert denied.status_code == 422
    assert denied.json()["error"]["code"] == "PERSONNEL_OUTSIDE_PM_UNIT"

    allowed = client.put(
        f"/work-plans/{plan_id}/members",
        headers=world.headers(client, "ops"),
        json={
            "leader_employee_id": outsider,
            "member_employee_ids": [world.employees["member"]],
            "row_version": created.json()["row_version"],
        },
    )
    assert allowed.status_code == 200, allowed.text
    assert sync_query(
        "SELECT employee_id::text FROM vms.work_plan_member WHERE work_plan_id = %s ORDER BY role_in_plan",
        (plan_id,),
    ) == [(outsider,), (world.employees["member"],)]


def test_assignment_options_fix_pm_scope_and_hide_conflicting_people(client, world: World):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=20, length_days=2)
    version = sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]
    team = client.put(
        f"/work-plans/{plan_id}/members",
        headers=world.headers(client, "pm"),
        json={
            "leader_employee_id": world.employees["leader"],
            "member_employee_ids": [world.employees["member"]],
            "row_version": version,
        },
    )
    published = client.post(
        f"/work-plans/{plan_id}/publish",
        headers=world.headers(client, "pm"),
        json={"row_version": team.json()["row_version"], "reason": ""},
    )
    assert published.status_code == 200, published.text
    start = jakarta_now().date() + timedelta(days=20)
    params = {"period_start": start.isoformat(), "period_end": (start + timedelta(days=1)).isoformat()}

    pm_options = client.get("/work-plans/assignment-options", headers=world.headers(client, "pm"), params=params)
    assert pm_options.status_code == 200, pm_options.text
    assert pm_options.json()["can_choose_pm"] is False
    assert pm_options.json()["fixed_pm_employee_id"] == world.employees["pm"]
    assert {person["id"] for person in pm_options.json()["personnel_options"]}.isdisjoint(
        {world.employees["leader"], world.employees["member"]}
    )

    ops_options = client.get("/work-plans/assignment-options", headers=world.headers(client, "ops"), params=params)
    assert ops_options.status_code == 200, ops_options.text
    assert ops_options.json()["can_choose_pm"] is True
    assert world.employees["pm"] in {person["id"] for person in ops_options.json()["pm_options"]}


def _patch_leader(client, world: World, who: str, plan: dict, leader: str):
    return client.patch(
        f"/work-plans/{plan['id']}",
        headers=world.headers(client, who),
        json={"leader_employee_id": leader, "row_version": plan["row_version"]},
    )


def test_patch_cannot_make_an_outsider_leader_for_a_pm(client, world: World):
    """R-26 (A-01): PATCH ketua dulu melewati cakupan unit PM (R-23)."""
    outsider = world.add_person("outsider_patch", None, unit_id=world.add_unit("OTHER_PATCH"))
    plan = client.post("/work-plans", headers=world.headers(client, "pm"),
                       json=_body(world, pm=world.employees["pm"])).json()

    response = _patch_leader(client, world, "pm", plan, outsider)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "PERSONNEL_OUTSIDE_PM_UNIT"
    assert sync_query("SELECT leader_employee_id FROM vms.work_plan WHERE id = %s", (plan["id"],)) == [(None,)]


def test_patch_cannot_make_office_staff_leader(client, world: World):
    """R-26 (A-01): peran kantor tidak boleh jadi ketua lewat PATCH, termasuk oleh OPS."""
    plan = client.post("/work-plans", headers=world.headers(client, "ops"),
                       json=_body(world, pm=world.employees["pm"])).json()

    response = _patch_leader(client, world, "ops", plan, world.employees["hr"])

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "PERSONNEL_NOT_FIELD_STAFF"
    assert sync_query("SELECT count(*) FROM vms.work_plan_member WHERE work_plan_id = %s", (plan["id"],)) == [(0,)]


def test_ops_may_patch_a_cross_unit_field_leader(client, world: World):
    outsider = world.add_person("outsider_patch_ops", None, unit_id=world.add_unit("OTHER_PATCH_OPS"))
    plan = client.post("/work-plans", headers=world.headers(client, "ops"),
                       json=_body(world, pm=world.employees["pm"])).json()

    response = _patch_leader(client, world, "ops", plan, outsider)

    assert response.status_code == 200, response.text
    assert sync_query("SELECT leader_employee_id::text FROM vms.work_plan WHERE id = %s",
                      (plan["id"],)) == [(outsider,)]
