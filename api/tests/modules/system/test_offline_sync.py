"""
M12 · Sinkronisasi luring (dok 02 A-08, dok 04 §7), daily-first (Milestone 5).
POST /sync/operations {device_id, operations:[{client_op_id, op_type, payload, client_created_at}]}
- Boleh luring: OVERTIME_REPORT (lembur atas jadwal harian ONGOING). Laporan harian & insiden SK V1 dipensiunkan.
- Tidak boleh luring (absensi, persetujuan, operasi lama) → REJECTED dengan alasan.
- Idempoten per (pengguna, client_op_id): kirim ulang mengembalikan hasil pertama, tidak menggandakan.
- Satu operasi gagal tidak menggagalkan yang lain; penolakan disimpan (GET /sync/status).
"""
from __future__ import annotations

import uuid

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan, run_daily_to_ongoing

pytestmark = requires_db

NOT_OFFLINE = "Aksi ini tidak dapat dikirim saat luring."


def _op(op_type: str, payload: dict) -> dict:
    return {"client_op_id": str(uuid.uuid4()), "op_type": op_type, "payload": payload,
            "client_created_at": jakarta_now().isoformat()}


def _sync(client, world: World, who: str, ops: list[dict]):
    return client.post("/sync/operations", headers=world.headers(client, who),
                       json={"device_id": f"hp-{who}", "operations": ops})


def test_overtime_syncs_idempotently(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    ops = [_op("OVERTIME_REPORT", {"daily_plan_id": plan_id, "hours": 2, "reason": "Menyelesaikan penarikan kabel"})]

    first = _sync(client, world, "leader", ops)
    assert first.status_code == 200, first.text
    assert [r["status"] for r in first.json()["results"]] == ["APPLIED"]

    again = _sync(client, world, "leader", ops)
    assert [r["status"] for r in again.json()["results"]] == ["APPLIED"]
    assert sync_query("SELECT count(*) FROM overtime WHERE daily_plan_id = %s", (plan_id,)) == [(1,)]


def test_rejections_are_kept_and_do_not_block_other_operations(client, world: World):
    ongoing = run_daily_to_ongoing(world)
    not_started = make_daily_plan(world, status="APPROVED", days_from_today=1)
    retired = _op("DAILY_REPORT_SAVE", {"plan_id": ongoing, "day_id": ongoing, "body": "x", "obstacle": "-"})
    wrong_state = _op("OVERTIME_REPORT", {"daily_plan_id": not_started, "hours": 1, "reason": "Belum mulai"})
    fine = _op("OVERTIME_REPORT", {"daily_plan_id": ongoing, "hours": 1, "reason": "Merapikan kabel"})

    response = _sync(client, world, "member", [retired, wrong_state, fine])

    assert response.status_code == 200, response.text
    results = {r["client_op_id"]: r for r in response.json()["results"]}
    assert results[retired["client_op_id"]] == {"client_op_id": retired["client_op_id"], "status": "REJECTED",
                                                "error_message": NOT_OFFLINE}
    assert results[wrong_state["client_op_id"]]["status"] == "REJECTED"
    assert results[fine["client_op_id"]]["status"] == "APPLIED"

    status = client.get("/sync/status", headers=world.headers(client, "member"))
    assert status.status_code == 200, status.text
    rejected = [op for op in status.json() if op["status"] == "REJECTED"]
    assert {op["client_op_id"] for op in rejected} == {retired["client_op_id"], wrong_state["client_op_id"]}
    assert all(op["error_message"] for op in rejected)
