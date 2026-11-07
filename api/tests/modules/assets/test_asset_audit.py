"""Audit buat/ubah/status/hapus alat dan kendaraan di app_activity_logs."""

from __future__ import annotations

import json

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool, create_vehicle

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _logs(action: str, entity_id: str) -> list[dict]:
    rows = sync_query(
        "SELECT changed_diff, entity_table, actor_user_id::text FROM app_activity_logs "
        "WHERE entity_id = %s AND action = %s ORDER BY created_at",
        (entity_id, action),
    )
    return [{"diff": r[0] if isinstance(r[0], dict) else json.loads(r[0]), "table": r[1], "actor": r[2]} for r in rows]


def test_tool_changes_are_audited(client, world: World):
    hr = world.headers(client, "hr")
    created = create_tool(client, world)
    assert created.status_code == 201, created.text
    tid = created.json()["tool_id"]
    log = _logs("TOOL_CREATE", tid)
    assert len(log) == 1 and log[0]["table"] == "tool" and log[0]["actor"]
    assert log[0]["diff"]["changes"]["name"] == {"new": "Bor uji"}

    assert client.put(f"/assets/tools/{tid}", headers=hr, json={"name": "Bor baru"}).status_code == 200
    upd = _logs("TOOL_UPDATE", tid)
    assert len(upd) == 1 and upd[0]["diff"]["changes"] == {"name": {"old": "Bor uji", "new": "Bor baru"}}

    assert client.post(f"/assets/tools/{tid}/status", headers=hr, json={"status": "damaged"}).status_code == 200
    st = _logs("TOOL_STATUS", tid)
    assert len(st) == 1 and st[0]["diff"]["changes"] == {"status": {"old": "ready", "new": "damaged"}}

    assert client.delete(f"/assets/tools/{tid}", headers=hr).status_code == 200
    dele = _logs("TOOL_DELETE", tid)
    assert len(dele) == 1 and dele[0]["diff"]["changes"]["tool_code"]["old"]


def test_vehicle_changes_are_audited(client, world: World):
    hr = world.headers(client, "hr")
    created = create_vehicle(client, world)
    assert created.status_code == 201, created.text
    vid = created.json()["vehicle_id"]
    assert len(_logs("VEHICLE_CREATE", vid)) == 1

    assert client.put(f"/assets/vehicles/{vid}", headers=hr, json={"name": "Mobil baru"}).status_code == 200
    upd = _logs("VEHICLE_UPDATE", vid)
    assert len(upd) == 1 and upd[0]["diff"]["changes"]["name"]["new"] == "Mobil baru"

    assert client.delete(f"/assets/vehicles/{vid}", headers=hr).status_code == 200
    assert len(_logs("VEHICLE_DELETE", vid)) == 1
