"""Audit buat/ubah/hapus klien dan site klien; PIC, telepon, alamat tidak disimpan nilainya."""

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


def test_client_and_site_changes_are_audited(client, world):
    pm = world.headers(client, "pm")
    made = client.post("/clients", headers=pm, json={
        "client_code": f"AU{world.tag}"[:20].upper(), "name": f"Klien Audit {world.tag}",
        "pic_name": "Budi Rahasia", "pic_phone": "081234567890", "address": "Jl. Rahasia 1"})
    assert made.status_code == 201, made.text
    cid = made.json()["client_id"]

    created = _logs("CLIENT_CREATE", cid)
    assert len(created) == 1 and created[0]["table"] == "client" and created[0]["actor"]
    assert created[0]["diff"]["changes"]["status"] == {"new": True}

    upd = client.put(f"/clients/{cid}", headers=pm,
                     json={"name": f"Klien Audit B {world.tag}", "pic_phone": "081111111"})
    assert upd.status_code == 200, upd.text
    log = _logs("CLIENT_UPDATE", cid)
    assert len(log) == 1
    assert log[0]["diff"]["changes"]["name"]["old"] == f"Klien Audit {world.tag}"
    assert log[0]["diff"]["masked_changed"] == ["pic_phone"]

    site = client.post(f"/clients/{cid}/sites", headers=pm, json={
        "site_name": "Cabang A", "address": "Jl. Site Rahasia", "latitude": "-6.2", "longitude": "106.8",
        "geofence_radius_meters": 120, "pic_name": "Siti", "pic_phone": "082222222"})
    assert site.status_code == 201, site.text
    sid = site.json()["site_id"]
    assert len(_logs("CLIENT_SITE_CREATE", sid)) == 1
    site_upd = client.put(f"/clients/{cid}/sites/{sid}", headers=pm, json={"geofence_radius_meters": 200})
    assert site_upd.status_code == 200
    up = _logs("CLIENT_SITE_UPDATE", sid)
    assert up[0]["diff"]["changes"]["geofence_radius_meters"] == {"old": 120, "new": 200}
    assert client.delete(f"/clients/{cid}/sites/{sid}", headers=pm).status_code == 200
    assert len(_logs("CLIENT_SITE_DELETE", sid)) == 1

    assert client.delete(f"/clients/{cid}", headers=pm).status_code == 200
    assert len(_logs("CLIENT_DELETE", cid)) == 1

    everything = json.dumps([x["diff"] for a, e in (
        ("CLIENT_CREATE", cid), ("CLIENT_UPDATE", cid), ("CLIENT_DELETE", cid),
        ("CLIENT_SITE_CREATE", sid), ("CLIENT_SITE_UPDATE", sid), ("CLIENT_SITE_DELETE", sid)) for x in _logs(a, e)])
    for secret in ("Rahasia", "081234567890", "081111111", "082222222", "Siti", "Budi"):
        assert secret not in everything
