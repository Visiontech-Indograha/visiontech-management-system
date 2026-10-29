"""
Kuota cuti tahunan: persetujuan tidak boleh melewati sisa kuota, dan dua peninjau tidak memotong kuota dua kali.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _next_workdays(n: int) -> tuple[str, str]:
    start = datetime.now(UTC).date() + timedelta(days=30)
    while start.weekday() == 6:
        start += timedelta(days=1)
    end = start
    for _ in range(n - 1):
        end += timedelta(days=1)
        if end.weekday() == 6:
            end += timedelta(days=1)
    return start.isoformat(), end.isoformat()


def test_approval_is_refused_when_the_remaining_quota_is_gone(client, world: World):
    start, end = _next_workdays(2)
    applied = client.post(
        "/leaves", headers=world.headers(client, "member"),
        json={"leave_type": "ANNUAL", "start_date": start, "end_date": end, "reason": "Keperluan uji"},
    )
    assert applied.status_code == 201, applied.text
    leave_id = applied.json()["leave_id"]
    # kuota habis setelah pengajuan (mis. pengajuan lain disetujui lebih dulu)
    sync_query("UPDATE leave_balance SET used_quota = total_quota WHERE employee_id = %s",
               (world.employees["member"],))

    refused = client.post(f"/leaves/{leave_id}/review", headers=world.headers(client, "hr"),
                          json={"decision": "APPROVED"})
    assert refused.status_code == 422, refused.text
    assert client.get(f"/leaves/{leave_id}", headers=world.headers(client, "hr")).json()["status"] == "PENDING"
