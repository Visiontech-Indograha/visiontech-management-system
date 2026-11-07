"""Audit buat/ubah/arsip/pulihkan karyawan; nama, telepon, PKWT, foto hanya nama bidang (tanpa nilai)."""

from __future__ import annotations

import json

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _logs(action: str, entity_id: str) -> list[dict]:
    rows = sync_query(
        "SELECT changed_diff, entity_table, actor_user_id::text FROM app_activity_logs "
        "WHERE entity_id = %s AND action = %s ORDER BY created_at",
        (entity_id, action),
    )
    return [{"diff": r[0] if isinstance(r[0], dict) else json.loads(r[0]), "table": r[1], "actor": r[2]} for r in rows]


def test_employee_changes_are_audited_without_personal_values(client, world: World):
    hr = world.headers(client, "hr")
    no = f"AUD-{world.tag}"
    created = client.post("/employees", headers=hr, json={
        "employee_no": no, "full_name": "Nama Rahasia Audit", "office_id": world.org_id,
        "division_id": world.unit_id or None, "join_date": "2026-01-05", "phone_number": "081234500011"})
    assert created.status_code == 201, created.text
    eid = created.json()["employee_id"]
    log = _logs("EMPLOYEE_CREATE", eid)
    assert len(log) == 1 and log[0]["table"] == "employee" and log[0]["actor"]
    assert log[0]["diff"]["changes"]["employee_no"] == {"new": no}

    upd = client.put(f"/employees/{eid}", headers=hr, json={
        "employee_no": f"{no}-B", "full_name": "Nama Baru Rahasia", "phone_number": "081299900022"})
    assert upd.status_code == 200, upd.text
    log = _logs("EMPLOYEE_UPDATE", eid)
    assert len(log) == 1
    assert log[0]["diff"]["changes"]["employee_no"] == {"old": no, "new": f"{no}-B"}
    assert sorted(log[0]["diff"]["masked_changed"]) == ["full_name", "phone_number"]

    sync_query("UPDATE employee SET offboarding_status = 'offboarded' WHERE employee_id = %s RETURNING 1", (eid,))
    assert client.post(f"/employees/{eid}/archive", headers=hr, json={}).status_code == 200
    assert len(_logs("EMPLOYEE_ARCHIVE", eid)) == 1
    assert client.post(f"/employees/{eid}/restore", headers=hr, json={}).status_code == 200
    assert len(_logs("EMPLOYEE_RESTORE", eid)) == 1

    everything = json.dumps([x["diff"] for a in (
        "EMPLOYEE_CREATE", "EMPLOYEE_UPDATE", "EMPLOYEE_ARCHIVE", "EMPLOYEE_RESTORE") for x in _logs(a, eid)])
    for secret in ("Rahasia", "081234500011", "081299900022"):
        assert secret not in everything
