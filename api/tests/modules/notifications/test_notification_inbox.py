"""Kotak masuk notifikasi: tersimpan di DB, terbaca lewat API, dan terkirim ke penerima yang tepat."""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db
from tests.modules.work_plans.test_daily_corrections import _ask, _completed_plan, _decide, _report

pytestmark = requires_db


def _inbox(client, world: World, who: str) -> dict:
    response = client.get("/notifications", headers=world.headers(client, who))
    assert response.status_code == 200, response.text
    return response.json()


def _kinds(client, world: World, who: str) -> list[str]:
    return [item["kind"] for item in _inbox(client, world, who)["items"]]


@pytest.mark.xdist_group("notification_inbox")
def test_correction_flow_notifies_pm_then_leader_and_marks_read(client, world: World) -> None:
    plan_id = _completed_plan(world)
    _report(client, world, plan_id)
    asked = _ask(client, world, plan_id)
    assert asked.status_code in (200, 201), asked.text

    pm_inbox = _inbox(client, world, "pm")
    assert "CORRECTION_REQUESTED" in [i["kind"] for i in pm_inbox["items"]]
    assert pm_inbox["unread"] >= 1

    decided = _decide(client, world, asked.json()["correction_id"], "APPROVE")
    assert decided.status_code == 200, decided.text
    leader_items = _inbox(client, world, "leader")["items"]
    assert any(i["kind"] == "CORRECTION_DECIDED" and i["daily_plan_id"] == plan_id for i in leader_items)

    one = next(i for i in leader_items if i["kind"] == "CORRECTION_DECIDED")
    read = client.post(f"/notifications/{one['id']}/read", headers=world.headers(client, "leader"))
    assert read.status_code == 200 and read.json()["updated"] == 1
    again = client.post(f"/notifications/{one['id']}/read", headers=world.headers(client, "leader"))
    assert again.json()["updated"] == 0

    client.post("/notifications/read-all", headers=world.headers(client, "pm"))
    assert _inbox(client, world, "pm")["unread"] == 0


def test_notifications_are_private_to_each_user(client, world: World) -> None:
    plan_id = _completed_plan(world)
    _report(client, world, plan_id)
    _ask(client, world, plan_id)
    assert "CORRECTION_REQUESTED" not in _kinds(client, world, "member")
