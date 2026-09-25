"""
V-15 · Trigger audit menemukan organisasi dari data baris itu sendiri. Tabel tanpa kolom
`organization_id` (asset_allocation, plan_change, plan_document, employee_document) sebelumnya
bergantung pada konteks sesi `app.organization_id`; tanpa konteks, `audit_event.organization_id`
NULL → operasinya gagal (NOT NULL), dan dengan konteks yang salah → tercatat di organisasi lain.
"""
from __future__ import annotations

from tests.conftest import requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _audit_org(entity_id: str, action: str) -> list[tuple]:
    return sync_query("SELECT organization_id::text FROM vms.audit_event WHERE entity_id = %s AND action = %s",
                      (entity_id, action))


def test_allocation_deleted_without_session_context_is_audited_in_its_organisation(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer = world.headers(client, "asset")
    asset_id = client.post("/assets", headers=officer, json={
        "kind": "TOOL", "code": "TL-AUDIT", "name": "Tangga", "condition": "BAIK"}).json()["id"]
    alloc_id = client.post(f"/assets/{asset_id}/reserve", headers=officer,
                           json={"work_plan_id": plan_id}).json()["id"]

    sync_query("DELETE FROM vms.asset_allocation WHERE id = %s", (alloc_id,))   # tanpa set_config

    assert _audit_org(alloc_id, "DELETE") == [(world.org_id,)]


def test_row_data_wins_over_a_wrong_session_context(client, world, other_world):
    """Konteks sesi organisasi lain tidak boleh membuat audit tercatat di organisasi itu."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    change_id = sync_query(
        "WITH _ctx AS (SELECT set_config('app.organization_id', %s, true)) "
        "INSERT INTO vms.plan_change (work_plan_id, change_type, reason, base_revision, proposed_revision, "
        "requested_by) SELECT id, 'EXTEND', 'Uji audit', revision, revision + 1, pm_employee_id "
        "FROM vms.work_plan, _ctx WHERE id = %s RETURNING id",
        (other_world.org_id, plan_id))[0][0]

    assert _audit_org(str(change_id), "INSERT") == [(world.org_id,)]


def test_employee_document_without_session_context_is_audited(client, world):
    doc_id = sync_query(
        "INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, uploaded_by) "
        "SELECT e.id, 'KTP', '****1111', u.id FROM vms.employee e JOIN vms.app_user u ON u.employee_id = e.id "
        "WHERE e.id = %s RETURNING id", (world.employees["member"],))[0][0]

    assert _audit_org(str(doc_id), "INSERT") == [(world.org_id,)]


def test_audit_events_never_show_another_organisation(client, world, other_world):
    """/audit-events disaring organization_id di SQL — tidak hanya bergantung pada RLS (T-12).
    work_plan termasuk tabel yang diaudit (db/02 tg_audit_row); asset tidak."""
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)

    own = client.get("/audit-events", headers=world.headers(client, "admin"),
                     params={"entity_type": "work_plan", "size": 100})
    assert own.status_code == 200
    assert plan_id in [e["entity_id"] for e in own.json()["items"]]
    foreign = client.get("/audit-events", headers=other_world.headers(client, "admin"),
                         params={"entity_type": "work_plan", "size": 100})
    assert foreign.status_code == 200
    assert plan_id not in [e["entity_id"] for e in foreign.json()["items"]]
