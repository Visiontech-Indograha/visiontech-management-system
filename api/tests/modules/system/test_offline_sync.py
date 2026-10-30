"""
M12 · Sinkronisasi offline (dok 02 A-08, dok 04 §7), daily-first (Milestone 5).
POST /sync/operations {device_id, operations:[{client_op_id, op_type, payload, client_created_at}]}
- Boleh offline: OVERTIME_REPORT dan DAILY_REPORT_SUBMIT untuk jadwal harian daily-first; insiden SK V1 dipensiunkan.
- Tidak boleh offline (absensi, persetujuan, operasi lama) → REJECTED dengan alasan.
- Idempoten per (pengguna, client_op_id): kirim ulang mengembalikan hasil pertama, tidak menggandakan.
- Satu operasi gagal tidak menggagalkan yang lain; penolakan disimpan (GET /sync/status).
"""
from __future__ import annotations

import uuid

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan, run_daily_to_ongoing

pytestmark = requires_db

NOT_OFFLINE = "Aksi ini tidak dapat dikirim saat offline."


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


def test_daily_report_syncs_idempotently(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    op = _op("DAILY_REPORT_SUBMIT", {
        "daily_plan_id": plan_id,
        "summary": "Pekerjaan harian selesai",
        "obstacles": "Tidak ada",
        "photos_json": [],
    })

    first = _sync(client, world, "leader", [op])
    assert first.status_code == 200, first.text
    assert [r["status"] for r in first.json()["results"]] == ["APPLIED"]

    again = _sync(client, world, "leader", [op])
    assert [r["status"] for r in again.json()["results"]] == ["APPLIED"]
    assert sync_query(
        "SELECT count(*) FROM work_plan_daily_report WHERE daily_plan_id = %s AND delete_at IS NULL",
        (plan_id,),
    ) == [(1,)]


def test_rejections_are_kept_and_do_not_block_other_operations(client, world: World):
    ongoing = run_daily_to_ongoing(world)
    not_started = make_daily_plan(world, status="APPROVED", days_from_today=1)
    retired = _op("DAILY_REPORT_SAVE", {"plan_id": ongoing, "day_id": ongoing, "body": "x", "obstacle": "-"})
    forbidden_report = _op("DAILY_REPORT_SUBMIT", {
        "daily_plan_id": ongoing,
        "summary": "Anggota bukan ketua",
        "photos_json": [],
    })
    wrong_state = _op("OVERTIME_REPORT", {"daily_plan_id": not_started, "hours": 1, "reason": "Belum mulai"})
    fine = _op("OVERTIME_REPORT", {"daily_plan_id": ongoing, "hours": 1, "reason": "Merapikan kabel"})

    response = _sync(client, world, "member", [retired, forbidden_report, wrong_state, fine])

    assert response.status_code == 200, response.text
    results = {r["client_op_id"]: r for r in response.json()["results"]}
    assert results[retired["client_op_id"]] == {"client_op_id": retired["client_op_id"], "status": "REJECTED",
                                                "error_message": NOT_OFFLINE}
    assert results[forbidden_report["client_op_id"]]["status"] == "REJECTED"
    assert results[wrong_state["client_op_id"]]["status"] == "REJECTED"
    assert results[fine["client_op_id"]]["status"] == "APPLIED"

    status = client.get("/sync/status", headers=world.headers(client, "member"))
    assert status.status_code == 200, status.text
    rejected = [op for op in status.json() if op["status"] == "REJECTED"]
    assert {op["client_op_id"] for op in rejected} == {
        retired["client_op_id"], forbidden_report["client_op_id"], wrong_state["client_op_id"]
    }
    assert all(op["error_message"] for op in rejected)


def _progress_item(client, world: World) -> tuple[str, str]:
    plan_id = make_daily_plan(world, status="DRAFT", days_from_today=0)
    wt = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                        (world.unit_id, f"Instalasi offline {world.tag}"))[0][0])
    created = client.post(f"/work-plans/daily/{plan_id}/items", headers=world.headers(client, "pm"), json={
        "work_type_id": wt, "title": "Titik offline", "task_phase": "INSTALLATION", "is_main_deliverable": True,
        "target_qty": "4"})
    assert created.status_code == 201, created.text
    sync_query("UPDATE work_plan_daily SET status = 'ONGOING' WHERE daily_plan_id = %s", (plan_id,))
    return plan_id, created.json()["item_id"]


def test_item_progress_syncs_and_rejects_over_target(client, world: World):
    _, item_id = _progress_item(client, world)
    ok = _op("PLAN_ITEM_PROGRESS", {"item_id": item_id, "completed_qty": 2, "notes": "Dikerjakan tanpa sinyal",
                                    "photos": [], "new_photo_requirements": []})
    first = _sync(client, world, "member", [ok])
    assert first.status_code == 200, first.text
    assert [r["status"] for r in first.json()["results"]] == ["APPLIED"]
    row = sync_query("SELECT completed_qty, notes FROM work_plan_item WHERE item_id = %s", (item_id,))[0]
    assert float(row[0]) == 2 and row[1] == "Dikerjakan tanpa sinyal"

    too_much = _op("PLAN_ITEM_PROGRESS", {"item_id": item_id, "completed_qty": 9, "photos": []})
    result = _sync(client, world, "member", [too_much]).json()["results"][0]
    assert result["status"] == "REJECTED" and "melebihi target" in result["error_message"]


def test_item_progress_from_outsider_is_rejected(client, world: World, other_world: World):
    _, item_id = _progress_item(client, world)
    op = _op("PLAN_ITEM_PROGRESS", {"item_id": item_id, "completed_qty": 1, "photos": []})
    result = _sync(client, other_world, "member", [op]).json()["results"][0]
    assert result["status"] == "REJECTED"


def test_rollover_request_syncs_offline(client, world: World):
    """Permintaan pindah hari dari HP lewat antrean: diterima seperti endpoint online (item → menunggu PM)."""
    _, item_id = _progress_item(client, world)
    op = _op("PLAN_ROLLOVER_REQUEST", {"item_id": item_id, "completed_qty": 1, "delay_reason": "Hujan deras"})
    result = _sync(client, world, "leader", [op]).json()["results"][0]
    assert result["status"] == "APPLIED", result
    row = sync_query("SELECT rollover_approval_status, delay_reason FROM work_plan_item WHERE item_id = %s",
                     (item_id,))[0]
    assert row[0] == "WAITING_PM" and row[1] == "Hujan deras"

    # Permintaan kedua untuk item yang sama ditolak (sudah menunggu PM), bukan digandakan.
    again = _op("PLAN_ROLLOVER_REQUEST", {"item_id": item_id, "completed_qty": 1, "delay_reason": "Hujan lagi"})
    assert _sync(client, world, "leader", [again]).json()["results"][0]["status"] == "REJECTED"
