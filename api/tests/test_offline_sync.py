"""
M12 · Sinkronisasi luring (dok 02 A-08, dok 04 §7, dok 05 §3.12).
POST /sync/operations {device_id, operations:[{client_op_id, op_type, payload, client_created_at}]}
- Boleh luring: DAILY_REPORT_SAVE, DAILY_REPORT_SUBMIT, TASK_TOGGLE, INCIDENT_REPORT, OVERTIME_REPORT.
- Tidak boleh luring (absensi, penerbitan, persetujuan) → REJECTED dengan alasan.
- Idempoten per (pengguna, client_op_id): kirim ulang mengembalikan hasil pertama, tidak menggandakan.
- Satu operasi gagal tidak menggagalkan yang lain; penolakan disimpan (GET /sync/status).
"""
from __future__ import annotations

import uuid

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _op(op_type: str, payload: dict) -> dict:
    return {"client_op_id": str(uuid.uuid4()), "op_type": op_type, "payload": payload,
            "client_created_at": jakarta_now().isoformat()}


def _sync(client, world: World, who: str, ops: list[dict]):
    return client.post("/sync/operations", headers=world.headers(client, who),
                       json={"device_id": f"hp-{who}", "operations": ops})


def test_field_actions_sync_idempotently(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    task_id = str(sync_query("SELECT id FROM vms.work_plan_task WHERE work_plan_day_id = %s", (day_ids[0],))[0][0])
    ops = [
        _op("TASK_TOGGLE", {"plan_id": plan_id, "day_id": day_ids[0], "task_id": task_id}),
        _op("DAILY_REPORT_SAVE", {"plan_id": plan_id, "day_id": day_ids[0],
                                  "body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"}),
        _op("DAILY_REPORT_SUBMIT", {"plan_id": plan_id, "day_id": day_ids[0]}),
        _op("OVERTIME_REPORT", {"work_plan_id": plan_id, "hours": 2, "reason": "Menyelesaikan penarikan kabel"}),
        _op("INCIDENT_REPORT", {"work_plan_id": plan_id, "category": "K3_RINGAN", "severity": "RENDAH",
                                "description": "Tangga licin di area kerja"}),
    ]

    first = _sync(client, world, "leader", ops)
    assert first.status_code == 200, first.text
    assert [r["status"] for r in first.json()["results"]] == ["APPLIED"] * 5
    assert sync_query("SELECT status::text, body FROM vms.daily_report WHERE work_plan_day_id = %s",
                      (day_ids[0],)) == [("SUBMITTED", "Kamera 1-4 terpasang dan diuji")]
    assert sync_query("SELECT is_done FROM vms.work_plan_task WHERE id = %s", (task_id,)) == [(True,)]

    again = _sync(client, world, "leader", ops)                       # kirim ulang → hasil pertama
    assert [r["status"] for r in again.json()["results"]] == ["APPLIED"] * 5
    assert sync_query("SELECT count(*) FROM vms.overtime_log WHERE work_plan_id = %s", (plan_id,)) == [(1,)]
    assert sync_query("SELECT count(*) FROM vms.incident_report WHERE work_plan_id = %s", (plan_id,)) == [(1,)]
    assert sync_query("SELECT is_done FROM vms.work_plan_task WHERE id = %s", (task_id,)) == [(True,)]


def test_rejections_are_kept_and_do_not_block_other_operations(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    not_leader = _op("DAILY_REPORT_SAVE", {"plan_id": plan_id, "day_id": day_ids[0],
                                           "body": "Isi dari anggota", "obstacle": "-"})
    forbidden_offline = _op("ATTENDANCE_CHECK_IN", {"site_id": world.site_id})
    fine = _op("OVERTIME_REPORT", {"work_plan_id": plan_id, "hours": 1, "reason": "Merapikan kabel"})

    response = _sync(client, world, "member", [not_leader, forbidden_offline, fine])

    assert response.status_code == 200, response.text
    results = {r["client_op_id"]: r for r in response.json()["results"]}
    assert results[not_leader["client_op_id"]]["status"] == "REJECTED"
    assert results[forbidden_offline["client_op_id"]]["status"] == "REJECTED"
    assert results[forbidden_offline["client_op_id"]]["error_message"] == "Aksi ini tidak dapat dikirim saat luring."
    assert results[fine["client_op_id"]]["status"] == "APPLIED"

    status = client.get("/sync/status", headers=world.headers(client, "member"))
    assert status.status_code == 200, status.text
    rejected = [op for op in status.json() if op["status"] == "REJECTED"]
    assert {op["client_op_id"] for op in rejected} == {not_leader["client_op_id"], forbidden_offline["client_op_id"]}
    assert all(op["error_message"] for op in rejected)
