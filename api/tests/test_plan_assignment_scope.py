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
