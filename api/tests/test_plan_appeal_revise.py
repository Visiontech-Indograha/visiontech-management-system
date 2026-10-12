"""
V-20 · APPEAL & REVISE (`domain.js` case APPEAL / REVISE).
- APPEAL: ketua menurut SK, hanya dari PUBLISHED, alasan wajib → APPEALED; dokumen lama tetap tercatat.
- REVISE: PM unit / OPS, hanya dari APPEALED → DRAFT, revision + 1, dokumen lama SUPERSEDED.
- Terbit ulang → dokumen versi baru berjenis REVISION (nomor SK sama); diterima → EFFECTIVE.
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_accepted

pytestmark = requires_db


def _rv(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def _published(client, world: World) -> str:
    plan_id, _ = create_draft_plan(client, world)
    pm = world.headers(client, "pm")
    assert client.put(f"/work-plans/{plan_id}/members", headers=pm, json={
        "leader_employee_id": world.employees["leader"], "member_employee_ids": [world.employees["member"]],
        "row_version": _rv(plan_id)}).status_code == 200
    assert client.post(f"/work-plans/{plan_id}/publish", headers=pm, json={"row_version": _rv(plan_id)}).status_code == 200
    return plan_id


def _do(client, world: World, plan_id: str, action: str, who: str, reason: str = "Lokasi tidak sesuai survei"):
    return client.post(f"/work-plans/{plan_id}/{action}", headers=world.headers(client, who),
                       json={"row_version": _rv(plan_id), "reason": reason})


def _plan(plan_id: str) -> tuple:
    return sync_query("SELECT status::text, revision, appeal_reason FROM vms.work_plan WHERE id = %s", (plan_id,))[0]


def _documents(plan_id: str) -> list[tuple]:
    return sync_query("SELECT version, kind::text, status::text FROM vms.plan_document WHERE work_plan_id = %s "
                      "ORDER BY version", (plan_id,))


# ── APPEAL ────────────────────────────────────────────────────────────────────────────────────
def test_leader_appeals_a_published_plan_with_a_reason(client, world):
    plan_id = _published(client, world)

    response = _do(client, world, plan_id, "appeal", "leader")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "APPEALED"
    assert _plan(plan_id) == ("APPEALED", 1, "Lokasi tidak sesuai survei")
    # Alur SK v2: dokumen yang menunggu tanda tangan menjadi Tidak berlaku (tetap tercatat).
    assert _documents(plan_id) == [(1, "INITIAL_ORDER", "SUPERSEDED")]


def test_appeal_needs_a_reason_the_leader_and_a_published_plan(client, world):
    plan_id = _published(client, world)

    empty = _do(client, world, plan_id, "appeal", "leader", reason="   ")
    assert empty.status_code == 422 and empty.json()["error"]["message"] in ("Alasan revisi wajib diisi.", "Alasan adendum wajib diisi.")
    for who in ("member", "pm"):
        assert _do(client, world, plan_id, "appeal", who).status_code == 403
    assert _plan(plan_id)[0] == "PUBLISHED"


def test_appeal_is_too_late_once_the_plan_is_accepted(client, world):
    accepted_id, _ = run_plan_to_accepted(client, world)
    late = _do(client, world, accepted_id, "appeal", "leader")
    assert late.status_code == 409 and late.json()["error"]["code"] == "INVALID_STATE"


# ── REVISE ────────────────────────────────────────────────────────────────────────────────────
def test_revise_reopens_the_draft_and_supersedes_old_documents(client, world):
    plan_id = _published(client, world)
    assert _do(client, world, plan_id, "appeal", "leader").status_code == 200

    assert _do(client, world, plan_id, "revise", "leader").status_code == 403
    revised = _do(client, world, plan_id, "revise", "pm")

    assert revised.status_code == 200, revised.text
    assert _plan(plan_id)[:2] == ("DRAFT", 2)
    assert _documents(plan_id) == [(1, "INITIAL_ORDER", "SUPERSEDED")]


def test_revise_only_from_appealed(client, world):
    plan_id = _published(client, world)

    response = _do(client, world, plan_id, "revise", "pm")

    assert response.status_code == 409 and response.json()["error"]["code"] == "INVALID_STATE"
    assert _plan(plan_id)[:2] == ("PUBLISHED", 1)


def test_full_revision_cycle_issues_a_revision_document(client, world):
    plan_id = _published(client, world)
    number = sync_query("SELECT number FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]
    assert _do(client, world, plan_id, "appeal", "leader").status_code == 200
    assert _do(client, world, plan_id, "revise", "pm").status_code == 200

    republished = client.post(f"/work-plans/{plan_id}/publish", headers=world.headers(client, "pm"),
                              json={"row_version": _rv(plan_id)})
    assert republished.status_code == 200, republished.text
    assert _documents(plan_id) == [(1, "INITIAL_ORDER", "SUPERSEDED"), (2, "REVISION", "AWAITING_ACCEPTANCE")]

    accepted = _do(client, world, plan_id, "accept", "leader")
    assert accepted.status_code == 200, accepted.text
    assert _documents(plan_id) == [(1, "INITIAL_ORDER", "SUPERSEDED"), (2, "REVISION", "EFFECTIVE")]
    assert sync_query("SELECT DISTINCT number FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,)) \
        == [(number,)]
