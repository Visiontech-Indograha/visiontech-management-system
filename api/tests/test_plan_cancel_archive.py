"""
V-21 · CANCEL_PLAN, DELETE_PLAN (arsip draf), RESTORE_PLAN (`domain.js`).
- Batal: PM unit/OPS, dari PUBLISHED/ACCEPTED/APPEALED/IN_PROGRESS/COMPLETION_REVIEW, alasan wajib;
  usulan perubahan terbuka & dokumen ikut ditarik (WITHDRAWN — skema tak punya CANCELLED; dok 10 C).
- Arsip: hanya DRAFT yang belum pernah punya SK, tanpa aset teralokasi, alasan wajib (soft delete).
- Pulihkan: hanya draf terarsip; tim diperiksa ulang (checkMembers).
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _rv(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def _do(client, world: World, plan_id: str, action: str, who: str = "pm", reason: str | None = "Pelanggan membatalkan"):
    body: dict = {"row_version": _rv(plan_id)}
    if reason is not None:
        body["reason"] = reason
    return client.post(f"/work-plans/{plan_id}/{action}", headers=world.headers(client, who), json=body)


def _team(client, world: World, plan_id: str) -> None:
    response = client.put(f"/work-plans/{plan_id}/members", headers=world.headers(client, "pm"), json={
        "leader_employee_id": world.employees["leader"], "member_employee_ids": [world.employees["member"]],
        "row_version": _rv(plan_id)})
    assert response.status_code == 200, response.text


# ── CANCEL_PLAN ───────────────────────────────────────────────────────────────────────────────
def test_cancel_withdraws_documents_and_open_changes(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    end = jakarta_now().date() + timedelta(days=5)
    change = client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, "leader"),
                         json={"type": "EXTEND", "new_period_end": end.isoformat(), "reason": "Material terlambat"})
    assert change.status_code == 201, change.text

    response = _do(client, world, plan_id, "cancel")

    assert response.status_code == 200, response.text
    assert sync_query("SELECT status::text, cancellation_reason FROM vms.work_plan WHERE id = %s", (plan_id,)) \
        == [("CANCELLED", "Pelanggan membatalkan")]
    assert sync_query("SELECT DISTINCT status::text FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,)) \
        == [("WITHDRAWN",)]
    assert sync_query("SELECT status::text FROM vms.plan_change WHERE work_plan_id = %s", (plan_id,)) \
        == [("WITHDRAWN",)]


def test_cancel_rules(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)

    missing = _do(client, world, plan_id, "cancel", reason="  ")
    assert missing.status_code == 422 and missing.json()["error"]["message"] == "Alasan pembatalan wajib diisi."
    assert _do(client, world, plan_id, "cancel", who="leader").status_code == 403
    assert _do(client, world, plan_id, "cancel", who="ops").status_code == 200       # OPS = PM lintas unit
    again = _do(client, world, plan_id, "cancel")
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_STATE"


def test_a_draft_is_archived_not_cancelled(client, world):
    plan_id, _ = create_draft_plan(client, world)

    response = _do(client, world, plan_id, "cancel")

    assert response.status_code == 409 and response.json()["error"]["code"] == "INVALID_STATE"


# ── DELETE_PLAN (arsip) & RESTORE_PLAN ────────────────────────────────────────────────────────
def test_archive_hides_the_draft_and_restore_brings_it_back(client, world):
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)
    pm = world.headers(client, "pm")

    archived = _do(client, world, plan_id, "archive", reason="Salah input unit")
    assert archived.status_code == 200, archived.text
    assert sync_query("SELECT deleted_at IS NOT NULL, deleted_by IS NOT NULL, deletion_reason FROM vms.work_plan "
                      "WHERE id = %s", (plan_id,)) == [(True, True, "Salah input unit")]
    assert client.get(f"/work-plans/{plan_id}", headers=pm).status_code == 404
    assert plan_id not in {p["id"] for p in client.get("/work-plans", headers=pm).json()}
    assert plan_id in {p["id"] for p in client.get("/work-plans", headers=pm, params={"archived": True}).json()}
    assert plan_id not in {p["id"] for p in client.get("/work-plans", headers=world.headers(client, "leader"),
                                                        params={"archived": True}).json()}

    restored = _do(client, world, plan_id, "restore", reason=None)
    assert restored.status_code == 200, restored.text
    assert client.get(f"/work-plans/{plan_id}", headers=pm).status_code == 200
    assert sync_query("SELECT deleted_at IS NULL, deleted_by IS NULL FROM vms.work_plan WHERE id = %s",
                      (plan_id,)) == [(True, True)]


def test_archive_rules(client, world):
    plan_id, _ = create_draft_plan(client, world)

    missing = _do(client, world, plan_id, "archive", reason="")
    assert missing.status_code == 422 and missing.json()["error"]["message"] == "Alasan pengarsipan wajib diisi."
    not_archived = _do(client, world, plan_id, "restore", reason=None)
    assert not_archived.status_code == 409 and not_archived.json()["error"]["message"] == "Draft tidak berada di arsip."

    officer = world.headers(client, "asset")
    asset_id = client.post("/assets", headers=officer, json={
        "kind": "TOOL", "code": "TL-ARSIP", "name": "Tangga", "condition": "BAIK"}).json()["id"]
    assert client.post("/assets/allocate", headers=officer,
                       json={"asset_id": asset_id, "work_plan_id": plan_id}).status_code == 200
    with_asset = _do(client, world, plan_id, "archive")
    assert with_asset.status_code == 409 and with_asset.json()["error"]["message"] == \
        "Lepaskan reservasi aset sebelum mengarsipkan draft."


def test_a_plan_that_once_had_an_sk_cannot_be_archived(client, world):
    """Draf hasil revisi pernah punya SK terbit → harus dibatalkan, bukan diarsipkan."""
    plan_id, _ = create_draft_plan(client, world)
    _team(client, world, plan_id)
    assert _do(client, world, plan_id, "publish", reason="").status_code == 200
    assert _do(client, world, plan_id, "appeal", who="leader", reason="Lokasi berubah").status_code == 200
    assert _do(client, world, plan_id, "revise", reason="").status_code == 200

    response = _do(client, world, plan_id, "archive")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == \
        "Pekerjaan yang pernah memiliki SK tidak dapat diarsipkan. Gunakan opsi pembatalan."


def test_restore_rechecks_the_team(client, world):
    plan_id, _ = create_draft_plan(client, world)                 # hanya ketua, belum ada anggota
    assert _do(client, world, plan_id, "archive").status_code == 200

    response = _do(client, world, plan_id, "restore", reason=None)

    assert response.status_code == 422 and response.json()["error"]["message"] == "Pilih minimal satu anggota tim."
    assert sync_query("SELECT deleted_at IS NOT NULL FROM vms.work_plan WHERE id = %s", (plan_id,)) == [(True,)]
