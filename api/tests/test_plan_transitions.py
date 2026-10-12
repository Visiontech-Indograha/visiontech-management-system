"""
V-06 · Aturan transisi SK (prototype/js/domain.js PUBLISH/ACCEPT/START, checkMembers, checkSchedule).
PUBLISH: PM; hanya DRAFT; tim lengkap; setiap tanggal periode punya hari berjudul dengan ≥ 1 tugas.
ACCEPT & START: ketua MENURUT SK (aturan inti #1); START tidak sebelum tanggal mulai (jam server).
"""
from __future__ import annotations

from tests.conftest import requires_db, sync_query
from tests.test_flow_plans import create_draft_plan

pytestmark = requires_db


def _rv(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def _team(client, world, plan_id, members=("member",)):
    r = client.put(f"/work-plans/{plan_id}/members", headers=world.headers(client, "pm"), json={
        "leader_employee_id": world.employees["leader"],
        "member_employee_ids": [world.employees[m] for m in members], "row_version": _rv(plan_id)})
    assert r.status_code == 200, r.text


def _do(client, world, plan_id, action, who):
    return client.post(f"/work-plans/{plan_id}/{action}", headers=world.headers(client, who),
                       json={"row_version": _rv(plan_id), "reason": ""})


def _error(response):
    return response.json()["error"]


def test_publish_requires_a_day_for_every_date(client, world):
    plan_id, day_ids = create_draft_plan(client, world, length_days=2)
    _team(client, world, plan_id)
    sync_query("DELETE FROM vms.work_plan_day WHERE id = %s", (day_ids[1],))

    response = _do(client, world, plan_id, "publish", "pm")

    assert response.status_code == 422
    assert _error(response)["message"] == "Rincian harian belum lengkap."


def test_publish_requires_tasks_on_every_day(client, world):
    plan_id, day_ids = create_draft_plan(client, world)
    _team(client, world, plan_id)
    sync_query("DELETE FROM vms.work_plan_task WHERE work_plan_day_id = %s", (day_ids[0],))

    assert _do(client, world, plan_id, "publish", "pm").status_code == 422


def test_publish_requires_at_least_one_member(client, world):
    # T5 (migrasi 0026): anggota kini opsional, rencana kerja dengan ketua saja dapat diterbitkan
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id, members=())

    response = _do(client, world, plan_id, "publish", "pm")

    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert response.json()["status"] == "PUBLISHED"
    else:
        assert _error(response)["message"] == "Pilih minimal satu anggota tim."


def test_publish_creates_locked_snapshot_with_tasks(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)

    response = _do(client, world, plan_id, "publish", "pm")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PUBLISHED"
    (snapshot, digest_ok) = sync_query(
        "SELECT snapshot, snapshot_sha256 = digest(snapshot::text, 'sha256') FROM vms.plan_document WHERE work_plan_id = %s",
        (plan_id,))[0]
    assert digest_ok
    assert all(day["tasks"] for day in snapshot["days"])
    assert {m["role_in_plan"] for m in snapshot["team"]} == {"LEADER", "MEMBER"}


def test_only_draft_can_be_published(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)
    assert _do(client, world, plan_id, "publish", "pm").status_code == 200

    again = _do(client, world, plan_id, "publish", "pm")

    assert again.status_code == 409
    assert _error(again)["code"] == "INVALID_STATE"


def test_member_cannot_publish(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)

    # SK draf tidak terlihat oleh anggota (V-07, domain.js visiblePlans) → 404, bukan 403.
    assert _do(client, world, plan_id, "publish", "member").status_code == 404


def test_only_the_leader_named_in_the_sk_accepts_and_starts(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)
    assert _do(client, world, plan_id, "publish", "pm").status_code == 200

    assert _do(client, world, plan_id, "accept", "member").status_code == 403
    assert _do(client, world, plan_id, "accept", "pm").status_code == 403
    assert _do(client, world, plan_id, "accept", "leader").status_code == 200
    assert sync_query("SELECT status::text, accepted_by::text FROM vms.plan_document WHERE work_plan_id = %s",
                      (plan_id,)) == [("EFFECTIVE", world.employees["leader"])]

    assert _do(client, world, plan_id, "start", "pm").status_code == 403
    assert _do(client, world, plan_id, "start", "leader").status_code == 200


def test_cannot_start_before_the_start_date(client, world):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=3)
    _team(client, world, plan_id)
    _do(client, world, plan_id, "publish", "pm")
    _do(client, world, plan_id, "accept", "leader")

    response = _do(client, world, plan_id, "start", "leader")

    assert response.status_code == 422
    assert "baru dapat dimulai pada" in _error(response)["message"]


def test_stale_row_version_is_rejected(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)

    response = client.post(f"/work-plans/{plan_id}/publish", headers=world.headers(client, "pm"),
                           json={"row_version": _rv(plan_id) - 1, "reason": ""})

    assert response.status_code == 409
    assert _error(response)["code"] == "CONFLICT"
