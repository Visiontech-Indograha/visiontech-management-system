"""
Laporan harian berjenjang (alur SK v2 PR2, services/member_report_service.py, flowchart SK2-E).
- PUT  /work-plans/{id}/days/{day}/member-report     anggota menyimpan draf (hanya SK Berjalan, tanggal sudah tiba)
- POST /work-plans/{id}/days/{day}/member-report/send  kirim ke ketua (uraian ≥ 10 karakter, sekali)
- GET  .../member-report (milik sendiri) · GET .../member-reports (daftar untuk ketua/PM)
- GET  .../report/html: dokumen A4 laporan harian — 404 selama ketua belum menyusunnya.
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_accepted, run_plan_to_in_progress

pytestmark = requires_db


def _url(plan_id: str, day_id: str, tail: str = "member-report") -> str:
    return f"/work-plans/{plan_id}/days/{day_id}/{tail}"


def _save(client, world: World, plan_id: str, day_id: str, body: str, who: str = "member", **extra):
    return client.put(_url(plan_id, day_id), headers=world.headers(client, who),
                      json={"body": body, "obstacle": extra.get("obstacle", ""),
                            "evidence_file_ids": extra.get("evidence_file_ids", [])})


def _send(client, world: World, plan_id: str, day_id: str, who: str = "member"):
    return client.post(_url(plan_id, day_id, "member-report/send"), headers=world.headers(client, who), json={})


def test_member_saves_sends_once_and_leader_sees_it(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    today = day_ids[0]

    assert client.get(_url(plan_id, today), headers=world.headers(client, "member")).json() is None
    not_saved = _send(client, world, plan_id, today)
    assert not_saved.status_code == 409 and not_saved.json()["error"]["message"] == "Simpan laporan dulu sebelum mengirim."

    short = _save(client, world, plan_id, today, "Selesai", obstacle="  Hujan  ")
    assert short.status_code == 200, short.text
    assert short.json()["status"] == "DRAFT" and short.json()["obstacle"] == "Hujan"
    too_short = _send(client, world, plan_id, today)
    assert too_short.status_code == 422 and too_short.json()["error"]["message"] == "Uraian laporan minimal 10 karakter."

    assert _save(client, world, plan_id, today, "  Kabel lantai 1 sudah ditarik  ").status_code == 200
    sent = _send(client, world, plan_id, today)
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "SENT" and sent.json()["sent_at"] is not None
    assert sent.json()["body"] == "Kabel lantai 1 sudah ditarik"

    locked = _save(client, world, plan_id, today, "Ubah setelah dikirim")
    assert locked.status_code == 409 and "sudah dikirim" in locked.json()["error"]["message"]
    again = _send(client, world, plan_id, today)
    assert again.status_code == 409 and again.json()["error"]["message"] == "Laporan sudah dikirim ke ketua."

    listed = client.get(_url(plan_id, today, "member-reports"), headers=world.headers(client, "leader"))
    assert listed.status_code == 200, listed.text
    assert [(r["employee_id"], r["status"]) for r in listed.json()] == [(world.employees["member"], "SENT")]
    assert sync_query("SELECT count(*) FROM vms.notification WHERE work_plan_id = %s AND kind ILIKE %s",
                      (plan_id, "%REPORT%"))[0][0] >= 1                          # ketua diberi tahu


def test_reports_wait_until_the_work_date(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    future = _save(client, world, plan_id, day_ids[1], "Belum waktunya bekerja")      # hari kedua = besok
    assert future.status_code == 422
    assert future.json()["error"]["message"] == "Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan."


def test_reports_only_on_running_plans(client, world):
    plan_id, day_ids = run_plan_to_accepted(client, world, start_offset_days=1)       # Diterima, belum berjalan
    not_running = _save(client, world, plan_id, day_ids[0], "SK belum berjalan sama sekali")
    assert not_running.status_code == 409, not_running.text
    assert not_running.json()["error"]["code"] == "INVALID_STATE"


def test_outsiders_cannot_read_or_write_member_reports(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    assert _save(client, world, plan_id, day_ids[0], "Laporan dari orang luar", who="hr").status_code in (403, 404)
    assert client.get(_url(plan_id, day_ids[0], "member-reports"),
                      headers=world.headers(client, "hr")).status_code in (403, 404)


def test_daily_report_document_waits_for_the_leader(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    response = client.get(_url(plan_id, day_ids[0], "report/html"), headers=world.headers(client, "pm"))
    assert response.status_code == 404
