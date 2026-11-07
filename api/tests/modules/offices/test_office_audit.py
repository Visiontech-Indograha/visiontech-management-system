"""Audit buat/ubah/hapus kantor: aksi, entitas, pelaku, nilai lama/baru; alamat tidak disimpan."""

from __future__ import annotations

import json

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def _logs(action: str, entity_id: str) -> list[dict]:
    rows = sync_query(
        "SELECT changed_diff, entity_table, actor_user_id::text FROM app_activity_logs "
        "WHERE entity_id = %s AND action = %s ORDER BY created_at",
        (entity_id, action),
    )
    return [{"diff": r[0] if isinstance(r[0], dict) else json.loads(r[0]), "table": r[1], "actor": r[2]} for r in rows]


def test_office_create_update_delete_are_audited(client, world):
    ops = world.headers(client, "ops")
    body = {"name": f"Audit {world.tag}", "address": "Jl. Rahasia 99", "location": {"lat": -6.2, "lng": 106.8},
            "radius_m": 150}
    created = client.post("/offices", headers=ops, json=body)
    assert created.status_code == 201, created.text
    oid = created.json()["id"]

    log = _logs("OFFICE_CREATE", oid)
    assert len(log) == 1 and log[0]["table"] == "office" and log[0]["actor"]
    assert log[0]["diff"]["changes"]["radius_m"] == {"new": 150}

    upd = client.put(f"/offices/{oid}", headers=ops, json={"radius_m": 300, "address": "Jl. Baru 1"})
    assert upd.status_code == 200, upd.text
    log = _logs("OFFICE_UPDATE", oid)
    assert len(log) == 1
    assert log[0]["diff"]["changes"]["radius_m"] == {"old": 150, "new": 300}
    assert log[0]["diff"]["masked_changed"] == ["address"]

    assert client.delete(f"/offices/{oid}", headers=ops).status_code == 200
    assert len(_logs("OFFICE_DELETE", oid)) == 1

    everything = json.dumps([x["diff"] for a in ("OFFICE_CREATE", "OFFICE_UPDATE", "OFFICE_DELETE")
                             for x in _logs(a, oid)])
    assert "Rahasia" not in everything and "Jl. Baru" not in everything
