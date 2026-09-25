"""
V-29 · SAVE_ATTACHMENTS (`domain.js`): PM unit/OPS mengganti seluruh lampiran SK selagi DRAFT;
lampiran ikut dibekukan di snapshot dokumen saat terbit (`domain.js` snapshot.attachments).
  PUT /work-plans/{id}/attachments {file_ids: [...]} · GET /work-plans/{id}/attachments
"""
from __future__ import annotations

import io

from PIL import Image

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import _row_version, create_draft_plan

pytestmark = requires_db


def _upload(client, world: World, colour: tuple[int, int, int], who: str = "pm") -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), colour).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("lampiran.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _save(client, world: World, plan_id: str, file_ids: list[str], who: str = "pm"):
    return client.put(f"/work-plans/{plan_id}/attachments", headers=world.headers(client, who),
                      json={"file_ids": file_ids})


def _stored(plan_id: str) -> list[tuple]:
    return sync_query("SELECT file_id::text, sort_order FROM vms.work_plan_attachment WHERE work_plan_id = %s "
                      "ORDER BY sort_order", (plan_id,))


def _publish(client, world: World, plan_id: str) -> None:
    pm = world.headers(client, "pm")
    members = client.put(f"/work-plans/{plan_id}/members", headers=pm, json={
        "leader_employee_id": world.employees["leader"],
        "member_employee_ids": [world.employees["member"]], "row_version": _row_version(plan_id)})
    assert members.status_code == 200, members.text
    published = client.post(f"/work-plans/{plan_id}/publish", headers=pm,
                            json={"row_version": _row_version(plan_id), "reason": ""})
    assert published.status_code == 200, published.text


def test_pm_replaces_the_attachments_of_a_draft(client, world, fake_storage):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)
    first, second = _upload(client, world, (10, 20, 30)), _upload(client, world, (40, 50, 60))

    saved = _save(client, world, plan_id, [second, first])
    assert saved.status_code == 200, saved.text
    assert [a["file_id"] for a in saved.json()] == [second, first]
    assert _stored(plan_id) == [(second, 0), (first, 1)]
    listed = client.get(f"/work-plans/{plan_id}/attachments", headers=world.headers(client, "pm"))
    assert listed.status_code == 200
    assert [(a["file_id"], a["file_name"]) for a in listed.json()] == [(second, "lampiran.png"), (first, "lampiran.png")]

    assert _save(client, world, plan_id, [first]).status_code == 200
    assert _stored(plan_id) == [(first, 0)]
    assert _save(client, world, plan_id, []).status_code == 200
    assert _stored(plan_id) == []


def test_attachment_rules(client, world, other_world, fake_storage):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)
    mine, foreign = _upload(client, world, (1, 2, 3)), _upload(client, other_world, (4, 5, 6))

    duplicate = _save(client, world, plan_id, [mine, mine])
    assert duplicate.status_code == 422 and duplicate.json()["error"]["message"] == "Lampiran tidak valid."
    assert _save(client, world, plan_id, [foreign]).status_code == 404
    assert _save(client, world, plan_id, [mine], who="member").status_code == 404   # draf tak terlihat anggota
    assert _stored(plan_id) == []


def test_attachments_are_frozen_in_the_published_document(client, world, fake_storage):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)
    file_id = _upload(client, world, (7, 8, 9))
    assert _save(client, world, plan_id, [file_id]).status_code == 200

    _publish(client, world, plan_id)

    snapshot = sync_query("SELECT snapshot -> 'attachments' FROM vms.plan_document WHERE work_plan_id = %s",
                          (plan_id,))[0][0]
    assert snapshot == [{"file_id": file_id, "file_name": "lampiran.png"}]
    locked = _save(client, world, plan_id, [])
    assert locked.status_code == 409 and locked.json()["error"]["code"] == "INVALID_STATE"
    assert _stored(plan_id) == [(file_id, 0)]
