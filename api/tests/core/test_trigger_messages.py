"""
Pesan aturan dari trigger basis data sampai ke pengguna (core/errors.trigger_rule_error).
Bentrok jadwal ketua saat membuat / mengubah SK sebelumnya berakhir 400 `DB_ERROR` generik
(membuat) atau 500 (mengubah ketua) — kini 409 `PERSONNEL_CONFLICT` dengan nomor SK yang bentrok,
sama dengan susunan tim (V-05).
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import requires_db, sync_query
from tests.modules.work_plans.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _busy_plan_number(client, world) -> str:
    plan_id, _ = run_plan_to_in_progress(client, world)        # ketua bertugas hari ini & besok
    return sync_query("SELECT number FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def test_creating_a_plan_with_a_busy_leader_explains_the_conflict(client, world):
    number = _busy_plan_number(client, world)
    today = jakarta_now().date()

    response = client.post("/work-plans", headers=world.headers(client, "pm"), json={
        "title": "SK bentrok", "unit_id": world.unit_id, "location_text": "Gudang uji",
        "period_start": today.isoformat(), "period_end": (today + timedelta(days=1)).isoformat(),
        "pm_employee_id": world.employees["pm"], "leader_employee_id": world.employees["leader"]})

    assert response.status_code == 409, response.text
    assert response.json()["error"] == {"code": "PERSONNEL_CONFLICT",
                                        "message": f"Jadwal personel bertabrakan dengan {number}.", "details": {}}
    assert sync_query("SELECT count(*) FROM vms.work_plan WHERE title = 'SK bentrok' AND organization_id = %s",
                      (world.org_id,)) == [(0,)]


def test_changing_to_a_busy_leader_is_409_not_500(client, world):
    number = _busy_plan_number(client, world)
    world.add_person("other_leader", None)  # R-26: ketua harus staf lapangan, bukan peran kantor
    draft_id, _ = create_draft_plan(client, world, leader="other_leader")   # periode sama, ketua lain
    row_version = sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (draft_id,))[0][0]

    response = client.patch(f"/work-plans/{draft_id}", headers=world.headers(client, "pm"),
                            json={"leader_employee_id": world.employees["leader"], "row_version": row_version})

    assert response.status_code == 409, response.text
    assert response.json()["error"]["message"] == f"Jadwal personel bertabrakan dengan {number}."
    assert sync_query("SELECT leader_employee_id::text FROM vms.work_plan WHERE id = %s", (draft_id,)) \
        == [(world.employees["other_leader"],)]
