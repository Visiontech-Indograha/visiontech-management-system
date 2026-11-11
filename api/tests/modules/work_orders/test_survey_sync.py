"""
Sinkron offline WO_SURVEY_SUBMIT: assign-survey -> team-surveys -> POST /sync/operations.
Idempoten (client_op_id diulang), cakupan tim (tim lain ditolak), konflik status (aman, tidak menimpa).
"""
from __future__ import annotations

import uuid

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.modules.work_orders.test_team_surveys import _assign, _ids, _new_wo, _other_team

pytestmark = requires_db


def _work_type(world: World) -> str:
    return str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                          (world.unit_id, f"Jenis {uuid.uuid4().hex[:6]}"))[0][0])


def _op(wo: str, wt: str) -> dict:
    point = {"point_name": "Titik A", "recommended_work_type_id": wt, "photos": [], "evidence_file_ids": []}
    payload = {"work_order_id": wo,
               "survey": {"narrative": "Survei HP", "format": "CCTV", "points": [point], "general_bom": []}}
    return {"client_op_id": str(uuid.uuid4()), "op_type": "WO_SURVEY_SUBMIT", "payload": payload,
            "client_created_at": jakarta_now().isoformat()}


def _sync(client, world: World, who: str, ops: list[dict]) -> dict:
    res = client.post("/sync/operations", headers=world.headers(client, who),
                      json={"device_id": f"hp-{who}", "operations": ops})
    assert res.status_code == 200, res.text
    body = res.json()
    rows = body["results"] if isinstance(body, dict) else body
    return rows[0]


def _status(wo: str) -> str:
    return sync_query("SELECT status FROM client_work_orders WHERE work_order_id = %s", (wo,))[0][0]


def _points(wo: str) -> int:
    return sync_query("SELECT COUNT(*) FROM work_order_survey_points WHERE work_order_id = %s", (wo,))[0][0]


def test_survey_sync_is_idempotent_and_hides_survey(client, world: World):
    wo, wt = _new_wo(world), _work_type(world)
    assert _assign(client, world, wo).status_code == 200
    assert _ids(client, world, "member") == [wo]
    op = _op(wo, wt)
    for _ in range(2):
        assert _sync(client, world, "member", [op])["status"] == "APPLIED"
    assert _status(wo) == "SURVEY_SUBMITTED" and _points(wo) == 1
    assert _ids(client, world, "leader") == []


def test_already_submitted_is_safe_noop_and_approved_is_rejected(client, world: World):
    wo, wt = _new_wo(world), _work_type(world)
    assert _assign(client, world, wo).status_code == 200
    assert _sync(client, world, "leader", [_op(wo, wt)])["status"] == "APPLIED"
    assert _sync(client, world, "member", [_op(wo, wt)])["status"] == "APPLIED"
    assert _points(wo) == 1
    sync_query("UPDATE client_work_orders SET status = 'READY_TO_EXECUTE' WHERE work_order_id = %s", (wo,))
    assert _sync(client, world, "leader", [_op(wo, wt)])["status"] == "REJECTED"
    assert _status(wo) == "READY_TO_EXECUTE"


def test_other_team_and_bad_payload_rejected(client, world: World):
    _other_team(world)
    wo, wt = _new_wo(world), _work_type(world)
    assert _assign(client, world, wo).status_code == 200
    assert _sync(client, world, "rival", [_op(wo, wt)])["status"] == "REJECTED"
    assert _sync(client, world, "leader", [_op(wo, str(uuid.uuid4()))])["status"] == "REJECTED"
    bad = _op(wo, wt)
    bad["payload"]["survey"]["points"][0].pop("point_name")
    assert _sync(client, world, "leader", [bad])["status"] == "REJECTED"
    assert _status(wo) != "SURVEY_SUBMITTED"


def test_work_types_readable_by_field_role(client, world: World):
    wt = _work_type(world)
    res = client.get("/work-types", headers=world.headers(client, "member"))
    assert res.status_code == 200 and wt in [r["id"] for r in res.json()]
