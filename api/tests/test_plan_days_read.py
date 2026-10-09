"""
GET /work-plans/{id}/days — hari kerja SK beserta tugas & laporan hariannya (dibutuhkan layar laporan
harian web/mobile; sebelumnya API hanya punya jalur tulis). Siapa pun yang melihat SK; tak terlihat → 404.
"""
from __future__ import annotations

from tests.conftest import World, requires_db
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _days(client, world: World, plan_id: str, who: str):
    return client.get(f"/work-plans/{plan_id}/days", headers=world.headers(client, who))


def test_team_reads_days_tasks_and_daily_report(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    leader = world.headers(client, "leader")
    task_id = client.get(f"/work-plans/{plan_id}/days", headers=leader).json()[0]["tasks"][0]["id"]
    assert client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/tasks/{task_id}/toggle", headers=leader,
                       json={}).status_code == 200
    assert client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=leader,
                      json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"}).status_code == 200

    response = _days(client, world, plan_id, "member")

    assert response.status_code == 200, response.text
    days = response.json()
    assert [d["id"] for d in days] == day_ids
    first, second = days
    assert [(t["title"], t["is_done"]) for t in first["tasks"]] == [("Pasang kamera", True)]
    # 2026-10-09 (pemilik): draf laporan ketua belum terlihat anggota/PM — hanya ketua.
    assert first["report"] is None
    assert second["report"] is None and second["tasks"][0]["is_done"] is False
    own = client.get(f"/work-plans/{plan_id}/days", headers=leader).json()[0]["report"]
    assert own["status"] == "DRAFT" and own["body"] == "Kamera 1-4 terpasang dan diuji"
    assert own["evidence_file_ids"] == []
    assert _days(client, world, plan_id, "pm").json()[0]["report"] is None

    assert client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/submit", headers=leader).status_code == 200
    sent = _days(client, world, plan_id, "member").json()[0]["report"]
    assert sent["status"] == "SUBMITTED" and sent["body"] == "Kamera 1-4 terpasang dan diuji"


def test_days_follow_plan_visibility(client, world: World, other_world: World):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)

    assert _days(client, world, plan_id, "pm").status_code == 200
    assert _days(client, world, plan_id, "member").status_code == 404     # draf tak terlihat anggota
    assert _days(client, other_world, plan_id, "pm").status_code == 404
