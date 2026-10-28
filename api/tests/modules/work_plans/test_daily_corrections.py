"""
Koreksi laporan harian: ketua mengajukan → PM setujui → ketua revisi & kirim → PM terima / kembalikan (berulang)
sampai diterima. Jadwal dibuka kembali (ONGOING) selama revisi dan COMPLETED lagi saat diterima.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query

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
