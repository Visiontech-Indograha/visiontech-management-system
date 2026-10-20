"""
V-24 · Tinjauan laporan harian (`domain.js` REVIEW_REPORT, SAVE_REPORT, SUBMIT_REPORT).

Jalur (dok 05 §3.6): POST /work-plans/{id}/days/{day_id}/review  {"decision": "APPROVE"|"RETURN", "note"}
- Hanya PM unit / OPS / ADMIN; SK IN_PROGRESS atau COMPLETION_REVIEW.
- Hanya laporan SUBMITTED, selain itu → 409 INVALID_STATE "Laporan belum menunggu pemeriksaan.".
- RETURN wajib catatan → 422 "Catatan revisi wajib diisi.". Keputusan lain → 422
  "Pilihan keputusan tidak dikenali. Muat ulang, lalu pilih lagi.".
- APPROVE → APPROVED; RETURN → CHANGES_REQUESTED; reviewed_by, reviewed_at, review_note tersimpan.
- Laporan CHANGES_REQUESTED boleh disunting & diajukan ulang oleh ketua; SUBMITTED/APPROVED tidak boleh
  disunting → 409 "Laporan yang sudah diserahkan tidak dapat diubah.".
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.modules.work_plans.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db

BODY = {"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"}


def _submitted(client, world: World) -> tuple[str, str]:
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    leader = world.headers(client, "leader")
    assert client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=leader, json=BODY).status_code == 200
    assert client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/submit", headers=leader).status_code == 200
    return plan_id, day_ids[0]


def _review(client, world: World, plan_id: str, day_id: str, who: str = "pm", **body):
    return client.post(f"/work-plans/{plan_id}/days/{day_id}/review", headers=world.headers(client, who), json=body)


def _report(day_id: str) -> tuple:
    return sync_query("SELECT status::text, review_note, reviewed_by IS NOT NULL, reviewed_at IS NOT NULL "
                      "FROM vms.daily_report WHERE work_plan_day_id = %s", (day_id,))[0]


def test_pm_approves_a_submitted_report(client, world):
    plan_id, day_id = _submitted(client, world)

    response = _review(client, world, plan_id, day_id, decision="APPROVE", note="Rapi")

    assert response.status_code == 200, response.text
    assert _report(day_id) == ("APPROVED", "Rapi", True, True)
    edit = client.put(f"/work-plans/{plan_id}/days/{day_id}", headers=world.headers(client, "leader"), json=BODY)
    assert edit.status_code == 409
    assert edit.json()["error"]["message"] == "Laporan yang sudah diserahkan tidak dapat diubah."


def test_returned_report_can_be_fixed_and_resubmitted(client, world):
    plan_id, day_id = _submitted(client, world)
    leader = world.headers(client, "leader")

    no_note = _review(client, world, plan_id, day_id, decision="RETURN", note="  ")
    assert no_note.status_code == 422 and no_note.json()["error"]["message"] == "Catatan revisi wajib diisi."
    returned = _review(client, world, plan_id, day_id, decision="RETURN", note="Lampirkan foto kamera 3")
    assert returned.status_code == 200, returned.text
    assert _report(day_id)[:2] == ("CHANGES_REQUESTED", "Lampirkan foto kamera 3")

    fixed = client.put(f"/work-plans/{plan_id}/days/{day_id}", headers=leader,
                       json={"body": "Kamera 1-4 terpasang, foto kamera 3 dilampirkan", "obstacle": "Tidak ada"})
    assert fixed.status_code == 200, fixed.text
    resubmitted = client.post(f"/work-plans/{plan_id}/days/{day_id}/submit", headers=leader)
    assert resubmitted.status_code == 200, resubmitted.text
    assert _report(day_id)[0] == "SUBMITTED"


def test_review_rules(client, world):
    plan_id, day_id = _submitted(client, world)

    assert _review(client, world, plan_id, day_id, who="leader", decision="APPROVE").status_code == 403
    assert _review(client, world, plan_id, day_id, who="member", decision="APPROVE").status_code == 403
    invalid = _review(client, world, plan_id, day_id, decision="MAYBE")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["message"] == "Pilihan keputusan tidak dikenali. Muat ulang, lalu pilih lagi."
    assert _review(client, world, plan_id, day_id, who="ops", decision="APPROVE").status_code == 200
    again = _review(client, world, plan_id, day_id, decision="APPROVE")
    assert again.status_code == 409 and again.json()["error"]["message"] == "Laporan belum menunggu pemeriksaan."


def test_draft_report_cannot_be_reviewed(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    assert client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=world.headers(client, "leader"),
                      json=BODY).status_code == 200

    response = _review(client, world, plan_id, day_ids[0], decision="APPROVE")

    assert response.status_code == 409 and response.json()["error"]["code"] == "INVALID_STATE"
