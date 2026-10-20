"""
V-25 · SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY (`domain.js`).
- Minggu = potongan 7 hari kerja SK (urut tanggal), hanya bila SK punya ≥ 7 hari; nama "Laporan Mingguan n".
- SAVE/SUBMIT: ketua menurut SK, SK IN_PROGRESS, laporan minggu itu DRAFT/CHANGES_REQUESTED.
  SUBMIT: semua laporan harian minggu itu APPROVED, isi > 10 karakter, kendala wajib diisi.
- REVIEW: PM unit/OPS, SK IN_PROGRESS/COMPLETION_REVIEW, laporan SUBMITTED; RETURN wajib catatan.
  GET /work-plans/{id}/weekly · PUT /work-plans/{id}/weekly/{n} · POST …/{n}/submit · POST …/{n}/review
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.modules.work_plans.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _url(plan_id: str, week: int, action: str = "") -> str:
    return f"/work-plans/{plan_id}/weekly/{week}" + (f"/{action}" if action else "")


def _approve_days(day_ids: list[str]) -> None:
    for day in day_ids:
        sync_query("INSERT INTO vms.daily_report (work_plan_day_id, status, body, obstacle) "
                   "VALUES (%s, 'APPROVED', 'Pekerjaan hari ini selesai', 'Tidak ada') "
                   "ON CONFLICT (work_plan_day_id) DO UPDATE SET status = 'APPROVED'", (day,))


def _week_row(plan_id: str, week: int) -> list[tuple]:
    return sync_query("SELECT status::text, body, obstacle, review_note FROM vms.weekly_report "
                      "WHERE work_plan_id = %s AND name = %s", (plan_id, f"Laporan Mingguan {week}"))


def test_weeks_follow_the_plan_days_and_access(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world, length_days=9)
    today = jakarta_now().date()

    weeks = client.get(f"/work-plans/{plan_id}/weekly", headers=world.headers(client, "member"))
    assert weeks.status_code == 200, weeks.text
    assert [(w["week"], w["name"], w["starts_on"], w["ends_on"], w["status"]) for w in weeks.json()] == [
        (1, "Laporan Mingguan 1", today.isoformat(), (today + timedelta(days=6)).isoformat(), "DRAFT"),
        (2, "Laporan Mingguan 2", (today + timedelta(days=7)).isoformat(),
         (today + timedelta(days=8)).isoformat(), "DRAFT"),
    ]

    body = {"body": "Instalasi minggu pertama", "obstacle": "Tidak ada"}
    assert client.put(_url(plan_id, 1), headers=world.headers(client, "member"), json=body).status_code == 403
    assert client.put(_url(plan_id, 1), headers=world.headers(client, "pm"), json=body).status_code == 403
    missing = client.put(_url(plan_id, 3), headers=world.headers(client, "leader"), json=body)
    assert missing.status_code == 404 and missing.json()["error"]["message"] == "Minggu tidak ditemukan."
    review = client.post(_url(plan_id, 1, "review"), headers=world.headers(client, "leader"),
                         json={"decision": "APPROVE"})
    assert review.status_code == 403
    assert _week_row(plan_id, 1) == []


def test_short_plan_has_no_weeks(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world)

    assert client.get(f"/work-plans/{plan_id}/weekly", headers=world.headers(client, "leader")).json() == []
    missing = client.put(_url(plan_id, 1), headers=world.headers(client, "leader"), json={"body": "x", "obstacle": ""})
    assert missing.status_code == 404


def test_weekly_report_save_submit_review(client, world: World):
    plan_id, day_ids = run_plan_to_in_progress(client, world, length_days=8)
    leader, pm = world.headers(client, "leader"), world.headers(client, "pm")

    saved = client.put(_url(plan_id, 1), headers=leader, json={"body": "Singkat", "obstacle": ""})
    assert saved.status_code == 200, saved.text
    assert _week_row(plan_id, 1) == [("DRAFT", "Singkat", "", None)]

    early = client.post(_url(plan_id, 1, "submit"), headers=leader)
    assert early.status_code == 409
    assert early.json()["error"]["message"] == \
        "Semua laporan harian dalam minggu ini harus disetujui terlebih dahulu."
    _approve_days(day_ids[:7])                                    # minggu 2 (hari ke-8) tidak ikut
    short = client.post(_url(plan_id, 1, "submit"), headers=leader)
    assert short.status_code == 422 and short.json()["error"]["message"] == "Laporan mingguan wajib diisi."
    client.put(_url(plan_id, 1), headers=leader, json={"body": "Kamera lantai 1-3 terpasang", "obstacle": " "})
    no_obstacle = client.post(_url(plan_id, 1, "submit"), headers=leader)
    assert no_obstacle.status_code == 422
    assert no_obstacle.json()["error"]["message"] == \
        'Ringkasan kendala mingguan wajib diisi (isi "Tidak ada" jika lancar).'

    client.put(_url(plan_id, 1), headers=leader, json={"body": "Kamera lantai 1-3 terpasang", "obstacle": "Tidak ada"})
    submitted = client.post(_url(plan_id, 1, "submit"), headers=leader)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "SUBMITTED"
    locked = client.put(_url(plan_id, 1), headers=leader, json={"body": "Ubah setelah serah", "obstacle": "-"})
    assert locked.status_code == 409 and locked.json()["error"]["message"] == "Laporan mingguan sudah diserahkan."

    no_note = client.post(_url(plan_id, 1, "review"), headers=pm, json={"decision": "RETURN", "note": " "})
    assert no_note.status_code == 422 and no_note.json()["error"]["message"] == "Catatan revisi wajib diisi."
    returned = client.post(_url(plan_id, 1, "review"), headers=pm, json={"decision": "RETURN", "note": "Lengkapi foto"})
    assert returned.status_code == 200, returned.text
    assert _week_row(plan_id, 1) == [("CHANGES_REQUESTED", "Kamera lantai 1-3 terpasang", "Tidak ada", "Lengkapi foto")]

    assert client.post(_url(plan_id, 1, "submit"), headers=leader).status_code == 200
    approved = client.post(_url(plan_id, 1, "review"), headers=pm, json={"decision": "APPROVE"})
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    again = client.post(_url(plan_id, 1, "review"), headers=pm, json={"decision": "APPROVE"})
    assert again.status_code == 409
    assert again.json()["error"]["message"] == "Laporan mingguan belum menunggu pemeriksaan."
    assert sync_query("SELECT submitted_by IS NOT NULL, reviewed_by IS NOT NULL FROM vms.weekly_report "
                      "WHERE work_plan_id = %s", (plan_id,)) == [(True, True)]
