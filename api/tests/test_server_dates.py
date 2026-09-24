"""
V-10 · Tanggal dari server (CLAUDE.md aturan 3 "jangan percaya perangkat", dok 07 R6).
"Hari ini" = tanggal menurut zona waktu organisasi (`organization.timezone`), dihitung dari jam
server — bukan jam perangkat, bukan tanggal kiriman klien, bukan zona waktu mesin (Docker = UTC).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.core.time import jakarta_now
from tests.conftest import requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

_CLOCK = re.compile(r"datetime\.(now|utcnow)\(|date\.today\(|time\.time\(")


def test_clock_is_read_only_in_core_time():
    """Standar backend: waktu hanya lewat core/time.py."""
    offenders = [
        f"{path.as_posix()}:{n}"
        for path in Path("app").rglob("*.py") if path.as_posix() != "app/core/time.py"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if _CLOCK.search(line)
    ]
    assert offenders == []


@requires_db
def test_daily_report_for_a_day_not_yet_reached_is_rejected(client, world):
    """R6 · domain.js SAVE_REPORT/SUBMIT_REPORT: hanya pada atau setelah tanggal pelaksanaan."""
    _, day_ids = run_plan_to_in_progress(client, world)   # hari ke-1 = hari ini, hari ke-2 = besok
    leader = world.headers(client, "leader")

    saved = client.post(f"/hse/daily-reports/{day_ids[1]}", headers=leader,
                        json={"body": "Kamera 5-8 terpasang dan diuji", "obstacle": "Tidak ada"})
    submitted = client.post(f"/hse/daily-reports/{day_ids[1]}/submit", headers=leader)

    for response in (saved, submitted):
        assert response.status_code == 422, response.text
        assert response.json()["error"]["message"] == "Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan."
    assert sync_query("SELECT count(*) FROM vms.daily_report WHERE work_plan_day_id = %s", (day_ids[1],)) == [(0,)]

    today = client.post(f"/hse/daily-reports/{day_ids[0]}", headers=leader,
                        json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"})
    assert today.status_code == 200, today.text


@requires_db
def test_incident_is_dated_today_by_the_server_not_by_the_client(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)

    response = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "occurred_on": "2020-01-01", "category": "K3_RINGAN",
        "severity": "RENDAH", "description": "Tangga licin di area kerja"})

    assert response.status_code == 201, response.text
    today = jakarta_now().date()
    assert date.fromisoformat(response.json()["occurred_on"]) == today
    assert sync_query("SELECT occurred_on FROM vms.incident_report WHERE id = %s", (response.json()["id"],)) \
        == [(today,)]


@requires_db
def test_attendance_work_date_follows_the_organisation_timezone(client, world):
    response = client.post("/attendance/check-in", headers=world.headers(client, "member"), json={
        "site_id": world.site_id, "location": {"lat": -6.2, "lng": 106.8}})

    assert response.status_code == 200, response.text
    assert sync_query("SELECT work_date FROM vms.attendance WHERE id = %s", (response.json()["id"],)) \
        == [(jakarta_now().date(),)]
