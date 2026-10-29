"""
Koreksi laporan harian: ketua mengajukan → PM setujui → ketua revisi & kirim → PM terima / kembalikan (berulang)
sampai diterima. Jadwal dibuka kembali (ONGOING) selama revisi dan COMPLETED lagi saat diterima.
"""
from __future__ import annotations

import json

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item

pytestmark = requires_db


def _completed_plan(world: World) -> str:
    return str(sync_query(
        "INSERT INTO work_plan_daily (work_date, site_name, site_lat, site_lng, division_id, team_id, "
        "created_by_id, status, approved_by_pm_id, approved_at) "
        "VALUES (CURRENT_DATE, 'Site uji', -6.2, 106.8, %s, %s, %s, 'COMPLETED', %s, now()) "
        "RETURNING daily_plan_id",
        (world.unit_id, world.team_id, world.employees["pm"], world.employees["pm"]))[0][0])


def _plan_status(plan_id: str) -> str:
    return str(sync_query("SELECT status FROM work_plan_daily WHERE daily_plan_id = %s", (plan_id,))[0][0])


def _report(client, world: World, plan_id: str, summary: str = "Pekerjaan selesai") -> None:
    response = client.post(f"/work-plans/daily/{plan_id}/report", headers=world.headers(client, "leader"),
                           json={"summary": summary, "obstacles": None, "photos_json": []})
    assert response.status_code in (200, 201), response.text


def _ask(client, world: World, plan_id: str, who: str = "leader"):
    return client.post(f"/work-plans/daily/{plan_id}/corrections", headers=world.headers(client, who),
                       json={"reason": "Jumlah unit salah tulis"})


def _decide(client, world: World, correction_id: str, decision: str, note: str | None = None, who: str = "pm"):
    return client.post(f"/work-plans/corrections/{correction_id}/decision", headers=world.headers(client, who),
                       json={"decision": decision, "note": note})


def test_full_loop_return_until_accepted(client, world: World):
    plan_id = _completed_plan(world)
    _report(client, world, plan_id)
    asked = _ask(client, world, plan_id)
    assert asked.status_code == 201, asked.text
    cid = asked.json()["correction_id"]
    assert asked.json()["status"] == "REQUESTED"

    assert _decide(client, world, cid, "APPROVE").json()["status"] == "REVISING"
    assert _plan_status(plan_id) == "ONGOING"

    leader = world.headers(client, "leader")
    submitted = client.post(f"/work-plans/corrections/{cid}/submit", headers=leader)
    assert submitted.json()["status"] == "IN_REVIEW" and submitted.json()["revision_count"] == 1

    returned = _decide(client, world, cid, "RETURN", "Lampirkan foto bukti")
    assert returned.json()["status"] == "REVISING" and returned.json()["review_note"] == "Lampirkan foto bukti"
    assert _plan_status(plan_id) == "ONGOING"

    assert client.post(f"/work-plans/corrections/{cid}/submit", headers=leader).json()["revision_count"] == 2
    accepted = _decide(client, world, cid, "ACCEPT")
    assert accepted.json()["status"] == "ACCEPTED"
    assert _plan_status(plan_id) == "COMPLETED"


def test_pm_can_reject_request_and_plan_stays_completed(client, world: World):
    plan_id = _completed_plan(world)
    cid = _ask(client, world, plan_id).json()["correction_id"]
    assert _decide(client, world, cid, "REJECT", "Tidak diperlukan").json()["status"] == "REJECTED"
    assert _plan_status(plan_id) == "COMPLETED"


@pytest.mark.parametrize("decision", ["REJECT", "RETURN"])
def test_reject_and_return_need_a_note(client, world: World, decision: str):
    cid = _ask(client, world, _completed_plan(world)).json()["correction_id"]
    assert _decide(client, world, cid, decision).status_code == 422


def test_only_leader_asks_and_only_pm_decides(client, world: World):
    plan_id = _completed_plan(world)
    assert _ask(client, world, plan_id, who="member").status_code == 403
    cid = _ask(client, world, plan_id).json()["correction_id"]
    assert _decide(client, world, cid, "APPROVE", who="leader").status_code == 403
    assert _decide(client, world, cid, "APPROVE", who="member").status_code in (403, 404)


def test_leader_cannot_close_plan_while_correction_is_open(client, world: World):
    """T7 (docs/diagram): saat koreksi REVISING jadwal berstatus ONGOING; /complete tidak boleh menutupnya."""
    plan_id = _completed_plan(world)
    _report(client, world, plan_id)
    cid = _ask(client, world, plan_id).json()["correction_id"]
    assert _decide(client, world, cid, "APPROVE").json()["status"] == "REVISING"
    assert _plan_status(plan_id) == "ONGOING"
    closed = client.post(f"/work-plans/daily/{plan_id}/complete", headers=world.headers(client, "leader"))
    assert closed.status_code == 409 and closed.json()["error"]["code"] == "CORRECTION_OPEN"
    assert _plan_status(plan_id) == "ONGOING"


def test_only_one_open_correction_and_only_when_completed(client, world: World):
    plan_id = _completed_plan(world)
    assert _ask(client, world, plan_id).status_code == 201
    assert _ask(client, world, plan_id).json()["error"]["code"] == "CORRECTION_OPEN"
    sync_query("UPDATE work_plan_daily SET status = 'ONGOING' WHERE daily_plan_id = %s", (plan_id,))
    other = _ask(client, world, plan_id)
    assert other.status_code == 409


def test_submit_needs_revising_state_and_report(client, world: World):
    plan_id = _completed_plan(world)
    cid = _ask(client, world, plan_id).json()["correction_id"]
    leader = world.headers(client, "leader")
    early = client.post(f"/work-plans/corrections/{cid}/submit", headers=leader)
    assert early.json()["error"]["code"] == "INVALID_STATE"
    _decide(client, world, cid, "APPROVE")
    no_report = client.post(f"/work-plans/corrections/{cid}/submit", headers=leader)
    assert no_report.json()["error"]["code"] == "REPORT_REQUIRED"


def test_inbox_scopes_to_division_and_leader(client, world: World):
    plan_id = _completed_plan(world)
    cid = _ask(client, world, plan_id).json()["correction_id"]
    for who in ("pm", "leader"):
        mine = client.get("/work-plans/corrections", headers=world.headers(client, who)).json()
        assert cid in [c["correction_id"] for c in mine]
    assert client.get("/work-plans/corrections", headers=world.headers(client, "member")).json() == []


def _ready_to_accept(client, world: World, plan_id: str) -> str:
    """Koreksi sampai IN_REVIEW (laporan ada, PM sudah menyetujui, ketua sudah mengirim revisi)."""
    _report(client, world, plan_id)
    cid = _ask(client, world, plan_id).json()["correction_id"]
    assert _decide(client, world, cid, "APPROVE").json()["status"] == "REVISING"
    submit = client.post(f"/work-plans/corrections/{cid}/submit", headers=world.headers(client, "leader"))
    assert submit.status_code == 200, submit.text
    return cid


def _done_item_missing_mandatory_photo(world: World, plan_id: str) -> tuple[str, str]:
    """Pekerjaan DONE dengan satu foto wajib (image_requirement) yang belum diunggah."""
    item = add_item(plan_id, world, "AP B", status="DONE", completed_qty=1, progress_percent=100)
    wt = sync_query("SELECT work_type_id FROM work_plan_item WHERE item_id = %s", (item,))[0][0]
    sync_query("INSERT INTO image_requirement (work_type_id, name, path_image, is_mandatory, sort_order) "
               "VALUES (%s, 'Foto sesudah', 'sop/x.png', TRUE, 1)", (wt,))
    req = str(sync_query("SELECT image_requirement_id FROM image_requirement WHERE work_type_id = %s", (wt,))[0][0])
    return item, req


def test_accept_refused_while_mandatory_photo_missing_then_forced_with_note(client, world: World):
    """F9: PM tidak boleh menerima koreksi bila foto wajib pekerjaan DONE belum lengkap (409 PHOTOS_INCOMPLETE)."""
    plan_id = _completed_plan(world)
    _done_item_missing_mandatory_photo(world, plan_id)
    cid = _ready_to_accept(client, world, plan_id)

    refused = _decide(client, world, cid, "ACCEPT")
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "PHOTOS_INCOMPLETE"
    assert "AP B" in refused.text and "Foto sesudah" in refused.text

    no_note = client.post(f"/work-plans/corrections/{cid}/decision", headers=world.headers(client, "pm"),
                          json={"decision": "ACCEPT", "force": True})
    assert no_note.status_code == 422, no_note.text

    forced = client.post(f"/work-plans/corrections/{cid}/decision", headers=world.headers(client, "pm"),
                         json={"decision": "ACCEPT", "force": True, "note": "Foto menyusul, sudah dicek di lokasi"})
    assert forced.status_code == 200, forced.text
    assert forced.json()["status"] == "ACCEPTED"
    assert _plan_status(plan_id) == "COMPLETED"


def test_accept_allowed_once_mandatory_photo_is_attached(client, world: World):
    plan_id = _completed_plan(world)
    item, req = _done_item_missing_mandatory_photo(world, plan_id)
    cid = _ready_to_accept(client, world, plan_id)
    sync_query("UPDATE work_plan_item SET realization_photos_json = %s::jsonb WHERE item_id = %s",
               (json.dumps([{"requirement_id": req}]), item))

    accepted = _decide(client, world, cid, "ACCEPT")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"
