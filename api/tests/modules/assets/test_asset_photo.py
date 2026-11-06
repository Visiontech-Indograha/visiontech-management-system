"""
Foto aset (alat): lima kondisi — kosong, data, ganti, tanpa izin, berkas tak ada / format salah.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db
from tests.modules.assets.test_asset_master import create_tool, upload

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]

NO_FILE = "00000000-0000-4000-8000-000000000000"


def _body(world: World, tag: str, **extra):
    return {"office_id": world.org_id, "division_id": world.unit_id, "ownership_type": "SHARED_TOOL",
            "category": "BOR", "name": "Bor foto", "tool_code": f"ph-{world.tag}-{tag}", **extra}


def test_tool_without_photo_has_null_photo(client, world: World):
    created = create_tool(client, world)
    assert created.status_code == 201, created.text
    assert created.json()["photo_file_id"] is None


def test_tool_with_photo_returns_file_id_in_create_and_list(client, world: World):
    hr = world.headers(client, "hr")
    file_id = upload(client, world, colour=11)
    created = client.post("/assets/tools", headers=hr, json=_body(world, "a", photo_file_id=file_id))
    assert created.status_code == 201, created.text
    assert created.json()["photo_file_id"] == file_id
    listed = client.get("/assets/tools", headers=hr).json()
    assert [t["photo_file_id"] for t in listed if t["tool_id"] == created.json()["tool_id"]] == [file_id]


def test_photo_can_be_replaced(client, world: World):
    hr = world.headers(client, "hr")
    created = client.post("/assets/tools", headers=hr,
                          json=_body(world, "b", photo_file_id=upload(client, world, colour=12))).json()
    second = upload(client, world, colour=13)
    put = client.put(f"/assets/tools/{created['tool_id']}", headers=hr, json={"photo_file_id": second})
    assert put.status_code == 200, put.text
    assert put.json()["photo_file_id"] == second


def test_photo_requires_asset_manager_role(client, world: World):
    file_id = upload(client, world, colour=14)
    denied = client.post("/assets/tools", headers=world.headers(client, "member"),
                         json=_body(world, "c", photo_file_id=file_id))
    assert denied.status_code in (403, 404)


def test_unknown_or_malformed_photo_is_rejected(client, world: World):
    hr = world.headers(client, "hr")
    missing = client.post("/assets/tools", headers=hr, json=_body(world, "d", photo_file_id=NO_FILE))
    assert missing.status_code == 422, missing.text
    bad = client.post("/assets/tools", headers=hr, json=_body(world, "e", photo_file_id="bukan-uuid"))
    assert bad.status_code == 422
