"""
V-26 · REQUEST_COMPLETE, APPROVE_COMPLETE, RETURN_COMPLETE (`domain.js`).
- REQUEST: ketua menurut SK, SK IN_PROGRESS, tak ada usulan perubahan terbuka, semua laporan harian &
  mingguan APPROVED, laporan akhir + ringkasan kendala wajib → SK COMPLETION_REVIEW, laporan akhir SUBMITTED.
- APPROVE: PM unit/OPS, SK COMPLETION_REVIEW, laporan akhir SUBMITTED, tak ada aset yang belum kembali
  → SK COMPLETED, laporan akhir APPROVED.
- RETURN: PM unit/OPS, alasan wajib → SK IN_PROGRESS, laporan akhir CHANGES_REQUESTED.
  POST /work-plans/{id}/request-completion · /approve-completion · /return-completion
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import _row_version, run_plan_to_in_progress
from tests.test_weekly_reports import _approve_days

pytestmark = requires_db

FINAL = {"body": "Seluruh kamera terpasang dan diuji", "obstacle": "Tidak ada"}


def _post(client, world: World, plan_id: str, action: str, who: str, **body):
    return client.post(f"/work-plans/{plan_id}/{action}", headers=world.headers(client, who),
                       json={"row_version": _row_version(plan_id), **body})


def _state(plan_id: str) -> list[tuple]:
    return sync_query("SELECT wp.status::text, fr.status::text, fr.review_note FROM vms.work_plan wp "
                      "LEFT JOIN vms.final_report fr ON fr.work_plan_id = wp.id WHERE wp.id = %s", (plan_id,))


def test_leader_requests_and_pm_approves_completion(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world)

    early = _post(client, world, plan_id, "request-completion", "leader", **FINAL)
    assert early.status_code == 409
    assert early.json()["error"]["message"] == "Seluruh laporan harian wajib disetujui PM terlebih dahulu."
    _approve_days(day_ids)
    empty = _post(client, world, plan_id, "request-completion", "leader", body="Selesai semua", obstacle=" ")
    assert empty.status_code == 422
    assert empty.json()["error"]["message"] == "Laporan penyelesaian dan ringkasan kendala keseluruhan wajib diisi."
    assert _post(client, world, plan_id, "request-completion", "member", **FINAL).status_code == 403
    assert _post(client, world, plan_id, "request-completion", "pm", **FINAL).status_code == 403

    requested = _post(client, world, plan_id, "request-completion", "leader", **FINAL)
    assert requested.status_code == 200, requested.text
    assert requested.json()["status"] == "COMPLETION_REVIEW"
    assert _state(plan_id) == [("COMPLETION_REVIEW", "SUBMITTED", None)]
    assert sync_query("SELECT body, obstacle, submitted_by IS NOT NULL, submitted_at IS NOT NULL "
                      "FROM vms.final_report WHERE work_plan_id = %s", (plan_id,)) \
        == [(FINAL["body"], FINAL["obstacle"], True, True)]

    assert _post(client, world, plan_id, "approve-completion", "leader").status_code == 403
    approved = _post(client, world, plan_id, "approve-completion", "pm", reason="Rapi")
    assert approved.status_code == 200, approved.text
    assert _state(plan_id) == [("COMPLETED", "APPROVED", "Rapi")]
    again = _post(client, world, plan_id, "approve-completion", "pm")
    assert again.status_code == 409


def test_pm_returns_completion_and_leader_resubmits(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    _approve_days(day_ids)
    assert _post(client, world, plan_id, "request-completion", "leader", **FINAL).status_code == 200

    no_reason = _post(client, world, plan_id, "return-completion", "pm", reason=" ")
    assert no_reason.status_code == 422 and no_reason.json()["error"]["message"] == "Alasan pengembalian wajib diisi."
    returned = _post(client, world, plan_id, "return-completion", "pm", reason="Lampirkan berita acara")
    assert returned.status_code == 200, returned.text
    assert _state(plan_id) == [("IN_PROGRESS", "CHANGES_REQUESTED", "Lampirkan berita acara")]

    again = _post(client, world, plan_id, "request-completion", "leader", **FINAL)
    assert again.status_code == 200, again.text
    assert _state(plan_id)[0][:2] == ("COMPLETION_REVIEW", "SUBMITTED")


def test_open_change_and_unfinished_weeks_block_completion(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world, length_days=7)
    _approve_days(day_ids)

    weekly = _post(client, world, plan_id, "request-completion", "leader", **FINAL)
    assert weekly.status_code == 409 and weekly.json()["error"]["message"] == "Laporan mingguan belum selesai."

    change = client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, "leader"),
                         json={"type": "EXTEND", "reason": "Hujan deras",
                               "new_period_end": (jakarta_now().date() + timedelta(days=9)).isoformat()})
    assert change.status_code == 201, change.text
    blocked = _post(client, world, plan_id, "request-completion", "leader", **FINAL)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["message"] == "Masih ada usulan perubahan yang belum selesai."
    assert _state(plan_id) == [("IN_PROGRESS", None, None)]
