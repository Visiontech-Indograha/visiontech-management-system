"""
Milestone 4 · Master aset: alat (tool) & kendaraan (vehicle) per kantor/divisi, berkas kendaraan (STNK/BPKB/KIR).
Kode alat & nomor polisi unik; status manual tidak boleh menimpa aset yang sedang dipinjam.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def upload(client, world: World, who: str = "hr", colour: int = 1) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (colour, 80, 40)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("aset.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def create_tool(client, world: World, ownership: str = "SHARED_TOOL", code: str | None = None):
    return client.post("/assets/tools", headers=world.headers(client, "hr"), json={
        "office_id": world.org_id, "division_id": world.unit_id, "ownership_type": ownership,
        "category": "BOR", "name": "Bor uji", "tool_code": code or f"tl-{world.tag}-{ownership[:3]}"})


def create_vehicle(client, world: World, vehicle_type: str = "Car", plate: str | None = None):
    return client.post("/assets/vehicles", headers=world.headers(client, "hr"), json={
        "office_id": world.org_id, "division_id": world.unit_id, "vehicle_type": vehicle_type,
        "name": "Kendaraan uji", "number_plate": plate or f"B {int(world.tag[:4], 16) % 9999 + 1} UJ"})


def test_tool_code_is_normalised_and_unique(client, world: World):
    created = create_tool(client, world, code="tl-bor-x1")
    assert created.status_code == 201, created.text
    assert created.json()["tool_code"] == "TL-BOR-X1"
    assert create_tool(client, world, code="TL-BOR-X1").json()["error"]["code"] == "TOOL_CODE_TAKEN"


def test_plate_is_normalised_and_unique(client, world: World):
    created = create_vehicle(client, world, plate="bk1999zz")
    assert created.status_code == 201, created.text
    assert created.json()["number_plate"] == "BK 1999 ZZ"
    assert create_vehicle(client, world, plate="BK 1999 ZZ").json()["error"]["code"] == "PLATE_TAKEN"


def test_only_asset_managers_create(client, world: World):
    response = client.post("/assets/tools", headers=world.headers(client, "pm"), json={
        "office_id": world.org_id, "ownership_type": "SHARED_TOOL", "category": "BOR", "name": "Bor",
        "tool_code": f"X-{world.tag}"})
    assert response.status_code == 403
    assert client.get("/assets/tools", headers=world.headers(client, "member")).status_code == 200


def test_vehicle_file_replaces_previous_and_feeds_expiry(client, world: World):
    vehicle_id = create_vehicle(client, world).json()["vehicle_id"]
    url = f"/assets/vehicles/{vehicle_id}/files"
    hr = world.headers(client, "hr")
    first = client.post(url, headers=hr, json={"type": "STNK", "file_id": upload(client, world, colour=1),
                                               "expired_at": "2030-01-01"})
    assert first.status_code == 201, first.text
    client.post(url, headers=hr, json={"type": "STNK", "file_id": upload(client, world, colour=2),
                                       "expired_at": "2031-06-30"})
    statuses = sorted(f["status"] for f in client.get(url, headers=hr).json())
    assert statuses == ["active", "extended"]
    vehicle = next(v for v in client.get("/assets/vehicles", headers=hr).json() if v["vehicle_id"] == vehicle_id)
    assert vehicle["stnk_expired_at"] == "2031-06-30"


def test_manual_status_and_delete(client, world: World):
    hr = world.headers(client, "hr")
    tool_id = create_tool(client, world).json()["tool_id"]
    assert client.post(f"/assets/tools/{tool_id}/status", headers=hr, json={"status": "damaged"}).json()["status"] \
        == "damaged"
    # allocated/loaned hanya lewat serah terima
    assert client.post(f"/assets/tools/{tool_id}/status", headers=hr, json={"status": "loaned"}).status_code == 422
    assert client.delete(f"/assets/tools/{tool_id}", headers=hr).status_code == 200
    assert tool_id not in [t["tool_id"] for t in client.get("/assets/tools", headers=hr).json()]
