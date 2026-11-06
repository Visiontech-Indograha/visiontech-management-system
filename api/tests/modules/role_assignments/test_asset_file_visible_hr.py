"""
`asset_file_visible` untuk HR terbatas (ADR 0002): foto/berkas aset hanya terbuka bagi HR yang kantornya meliputi aset
(atau pemegangnya); di luar itu 404. Flag mati = HR melihat semua (perilaku lama).
"""
from __future__ import annotations

import hashlib

import pytest

from app.core.config import settings
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

HR = "ADMIN_HR_GA"


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)


def _file(w: World, salt: str = "") -> tuple[str, str]:
    key = "uji-aset/" + hashlib.sha256(f"{w.tag}-{w.org_id}{salt}".encode()).hexdigest()[:24] + ".jpg"
    fid = sync_query(
        "INSERT INTO file_object (office_id, storage_key, file_name, mime_type, byte_size, sha256) "
        "VALUES (%s, %s, 'foto.jpg', 'image/jpeg', 10, decode(%s, 'hex')) RETURNING id::text",
        (w.org_id, key, hashlib.sha256(key.encode()).hexdigest()))[0][0]
    return fid, key


def _tool(client, w: World, code: str, key: str) -> str:
    r = client.post("/assets/tools", headers=w.headers(client, "admin"), json={
        "office_id": w.org_id, "division_id": w.unit_id, "ownership_type": "SHARED_TOOL", "category": "BOR",
        "name": "Bor uji", "tool_code": f"{code}-{w.tag}"})
    assert r.status_code == 201, r.text
    tool_id = r.json()["tool_id"]
    sync_query("UPDATE tool SET photo_path = %s WHERE tool_id = %s", (key, tool_id))
    return tool_id


@pytest.fixture
def photos(client, world: World, other_world: World):
    mine_id, mine_key = _file(world)
    theirs_id, theirs_key = _file(other_world)
    mine_tool, theirs_tool = _tool(client, world, "fm", mine_key), _tool(client, other_world, "ft", theirs_key)
    yield mine_id, theirs_id, mine_tool, theirs_tool
    sync_query("DELETE FROM asset_assignment WHERE tool_id IN (%s, %s)", (mine_tool, theirs_tool))
    sync_query("DELETE FROM tool WHERE tool_id IN (%s, %s)", (mine_tool, theirs_tool))
    sync_query("DELETE FROM file_object WHERE id IN (%s, %s)", (mine_id, theirs_id))


def _status(client, w: World, who: str, file_id: str) -> int:
    return client.get(f"/files/{file_id}/url", headers=w.headers(client, who)).status_code


def test_flag_on_hr_only_own_office_photo(client, world: World, other_world: World, photos, flag_on):
    mine, theirs, *_ = photos
    assert _status(client, world, "hr", mine) == 200
    assert _status(client, world, "hr", theirs) == 404
    assert _status(client, other_world, "hr", theirs) == 200
    assert _status(client, other_world, "hr", mine) == 404


def test_flag_on_hr_with_second_office_sees_both(client, world: World, other_world: World, photos, flag_on):
    mine, theirs, *_ = photos
    r = client.post(f"/users/{world.users['hr']}/role-assignments", headers=world.headers(client, "admin"),
                    json={"role": HR, "office_id": other_world.org_id})
    assert r.status_code == 201, r.text
    assert _status(client, world, "hr", mine) == 200
    assert _status(client, world, "hr", theirs) == 200


def test_flag_on_holder_sees_handover_photo_outsider_does_not(client, world: World, other_world: World,
                                                             photos, flag_on):
    mine_tool = photos[2]
    handover_id, handover_key = _file(world, "-h")
    try:
        lent = client.post("/assets/loans", headers=world.headers(client, "admin"), json={
            "asset_type": "TOOL", "tool_id": mine_tool, "employee_id": world.employees["member"]})
        assert lent.status_code == 201, lent.text
        sync_query("UPDATE tool SET photo_path = NULL WHERE tool_id = %s", (mine_tool,))
        sync_query("UPDATE asset_assignment SET handover_photo_path = %s WHERE assignment_id = %s",
                   (handover_key, lent.json()["assignment_id"]))
        assert _status(client, world, "member", handover_id) == 200
        assert _status(client, other_world, "member", handover_id) == 404
        assert _status(client, other_world, "hr", handover_id) == 404
        assert _status(client, world, "hr", handover_id) == 200
    finally:
        sync_query("UPDATE asset_assignment SET handover_photo_path = NULL WHERE tool_id = %s", (mine_tool,))
        sync_query("DELETE FROM file_object WHERE id = %s", (handover_id,))


def test_flag_off_hr_sees_all_offices(client, world: World, other_world: World, photos, flag_off):
    mine, theirs, *_ = photos
    assert _status(client, world, "hr", mine) == 200
    assert _status(client, world, "hr", theirs) == 200
