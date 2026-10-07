"""
Adendum saat SK Berjalan (alur SK v2 PR3, services/plan_amendment_service.py, flowchart SK2-E).
ketua mengajukan (alasan wajib, satu usulan terbuka) → SK tetap Berjalan → PM menolak (catatan wajib) atau
menerima dengan mengubah isi SK (ketua & tanggal mulai tetap; hari berlaporan tidak boleh dihapus) → dokumen
ADDENDUM ditandatangani PM → ketua menerima → adendum berlaku, versi SK lama Tidak berlaku.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _period(plan_id: str) -> tuple[date, date]:
    start, end = sync_query("SELECT lower(period), upper(period) - 1 FROM vms.work_plan WHERE id = %s", (plan_id,))[0]
    return start, end


def _amended(world: World, plan_id: str, *, extra_days: int = 1, **override: Any) -> dict[str, Any]:
    start, end = _period(plan_id)
    end = end + timedelta(days=extra_days)
    body: dict[str, Any] = {
        "title": "Instalasi CCTV gudang (adendum)", "description": "Tambah 2 kamera", "category": "INSTALASI",
        "site_id": world.site_id, "period_start": start.isoformat(), "period_end": end.isoformat(),
        "days": [{"work_date": (start + timedelta(days=i)).isoformat(),
                  "tasks": [{"title": f"Pekerjaan hari {i + 1}", "description": "Rincian adendum"}]}
                 for i in range((end - start).days + 1)],
        "leader_employee_id": world.employees["leader"], "member_employee_ids": [world.employees["member"]],
    }
    body.update(override)
    return body


def _request(client, world: World, plan_id: str, reason: str = "Klien menambah titik kamera", who: str = "leader"):
    return client.post(f"/work-plans/{plan_id}/amendments", headers=world.headers(client, who), json={"reason": reason})


def _open_change(plan_id: str) -> str:
    return str(sync_query("SELECT id FROM vms.plan_change WHERE work_plan_id = %s AND change_type = 'AMENDMENT' "
                          "ORDER BY created_at DESC LIMIT 1", (plan_id,))[0][0])


def _change_status(change_id: str) -> str:
    return sync_query("SELECT status::text FROM vms.plan_change WHERE id = %s", (change_id,))[0][0]


def test_leader_requests_and_pm_rejects_with_a_note(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)

    blank = _request(client, world, plan_id, reason="  ")
    assert blank.status_code == 422 and blank.json()["error"]["message"] == "Alasan adendum wajib diisi."
    assert _request(client, world, plan_id, who="member").status_code in (403, 404)   # bukan ketua menurut SK

    requested = _request(client, world, plan_id)
    assert requested.status_code == 200, requested.text
    assert [(c["change_type"], c["status"]) for c in requested.json()] == [("AMENDMENT", "PENDING_PM")]
    assert sync_query("SELECT status::text FROM vms.work_plan WHERE id = %s", (plan_id,)) == [("IN_PROGRESS",)]
    again = _request(client, world, plan_id)
    assert again.status_code == 409                                                # satu usulan terbuka per SK

    change = _open_change(plan_id)
    pm = world.headers(client, "pm")
    no_note = client.post(f"/work-plans/{plan_id}/amendments/{change}/reject", headers=pm, json={"reason": ""})
    assert no_note.status_code == 422 and no_note.json()["error"]["message"] == "Catatan penolakan wajib diisi."
    rejected = client.post(f"/work-plans/{plan_id}/amendments/{change}/reject", headers=pm,
                           json={"reason": "Anggaran belum disetujui klien"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()[0]["status"] == "REJECTED"
    assert rejected.json()[0]["decision_reason"] == "Anggaran belum disetujui klien"
    listed = client.get(f"/work-plans/{plan_id}/changes", headers=world.headers(client, "leader"))
    assert [c["status"] for c in listed.json()] == ["REJECTED"]                   # tulis → baca ulang
    twice = client.post(f"/work-plans/{plan_id}/amendments/{change}/reject", headers=pm, json={"reason": "lagi"})
    assert twice.status_code == 409                                                # sudah diputuskan


def test_pm_applies_amendment_and_leader_accepts(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    _, old_end = _period(plan_id)
    assert _request(client, world, plan_id).status_code == 200
    change = _open_change(plan_id)
    pm = world.headers(client, "pm")
    url = f"/work-plans/{plan_id}/amendments/{change}"

    other_leader = client.put(url, headers=pm, json=_amended(
        world, plan_id, leader_employee_id=world.employees["member"], member_employee_ids=[world.employees["leader"]]))
    assert other_leader.status_code == 422
    assert other_leader.json()["error"]["message"] == "Ketua tim tidak dapat diganti lewat adendum ini."
    start, _ = _period(plan_id)
    moved = _amended(world, plan_id)
    moved["period_start"] = (start + timedelta(days=1)).isoformat()
    moved["days"] = moved["days"][1:]
    assert client.put(url, headers=pm, json=moved).json()["error"]["message"] \
        == "Tanggal mulai SK yang sedang berjalan tidak dapat diubah."
    assert client.put(url, headers=world.headers(client, "leader"), json=_amended(world, plan_id)).status_code \
        in (403, 404)                                                              # hanya PM unit

    applied = client.put(url, headers=pm, json=_amended(world, plan_id))
    assert applied.status_code == 200, applied.text
    assert applied.json()["plan"]["title"] == "Instalasi CCTV gudang (adendum)"
    assert len(applied.json()["days"]) == 3
    assert _period(plan_id)[1] == old_end + timedelta(days=1)
    assert _change_status(change) == "AWAITING_LEADER_ACCEPTANCE"
    assert sync_query("SELECT kind::text FROM vms.plan_document WHERE work_plan_id = %s ORDER BY version", (plan_id,)) \
        == [("INITIAL_ORDER",), ("ADDENDUM",)]
    revision_before = sync_query("SELECT revision FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]

    accepted = client.post(f"{url}/accept", headers=world.headers(client, "leader"), json={})
    assert accepted.status_code == 200, accepted.text
    assert _change_status(change) == "EFFECTIVE"
    assert sync_query("SELECT kind::text, status::text FROM vms.plan_document WHERE work_plan_id = %s ORDER BY version",
                      (plan_id,)) == [("INITIAL_ORDER", "SUPERSEDED"), ("ADDENDUM", "EFFECTIVE")]
    assert sync_query("SELECT revision FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0] > revision_before
    assert client.post(f"{url}/accept", headers=world.headers(client, "leader"), json={}).status_code == 409


def test_amendment_cannot_remove_a_day_that_already_has_reports(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    saved = client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}/member-report", headers=world.headers(client, "member"),
                       json={"body": "Kabel lantai 1 sudah ditarik", "obstacle": ""})
    assert saved.status_code == 200, saved.text
    assert _request(client, world, plan_id).status_code == 200
    change = _open_change(plan_id)

    start, end = _period(plan_id)
    later = _amended(world, plan_id, extra_days=0)
    later["days"] = later["days"][1:]                       # buang hari pertama yang sudah berlaporan
    later["period_start"] = start.isoformat()
    response = client.put(f"/work-plans/{plan_id}/amendments/{change}", headers=world.headers(client, "pm"), json=later)
    assert response.status_code == 422
    assert response.json()["error"]["message"] in (
        f"Hari {start.isoformat()} sudah berlaporan dan tidak dapat dihapus.",
        "Setiap tanggal dalam rentang work plan wajib punya detail pekerjaan.")
    assert _change_status(change) == "PENDING_PM"                                    # tidak ada yang berubah
