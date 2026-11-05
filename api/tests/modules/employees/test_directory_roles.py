"""
Direktori & foto profil lintas divisi (audit cakupan). Finance dan HSE hanya melihat karyawan yang terlihat
menurut aturan direktori (diri sendiri, sesama divisi, sesama tim, jangkauan PM). HR, OM, SA, dan pengelola
aset/divisi tetap melihat seluruh karyawan. Foto profil mengikuti aturan yang sama: di luar cakupan → 404.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _setup_far_employee(world: World) -> str:
    """Karyawan di divisi lain (tanpa tim) — di luar cakupan finance & HSE."""
    unit2 = world.add_unit("Jauh")
    return world.add_person("far", None, unit_id=unit2)


def _directory_ids(client, world: World, who: str) -> set[str]:
    response = client.get("/employees", headers=world.headers(client, who), params={"size": 100})
    assert response.status_code == 200, response.text
    return {row["employee_id"] for row in response.json()["items"]}


def test_finance_and_hse_see_only_their_scope_in_directory(client, world: World):
    far = _setup_far_employee(world)
    world.add_person("fin", "FINANCE")
    world.add_person("hse", "HSE")
    for who in ("fin", "hse"):
        ids = _directory_ids(client, world, who)
        assert world.employees[who] in ids, who
        assert world.employees["member"] in ids, who  # sesama divisi
        assert far not in ids, who

    for who in ("hr", "ops", "admin"):
        assert far in _directory_ids(client, world, who), who


def test_finance_cannot_open_profile_photo_of_other_division(client, world: World):
    far = _setup_far_employee(world)
    world.add_person("fin", "FINANCE")
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (200, 40, 40)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, "hr"),
                           files={"file": ("foto.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    file_id = uploaded.json()["file_id"]
    set_photo = client.put(f"/employees/{far}", headers=world.headers(client, "hr"),
                           json={"photo_file_id": file_id})
    assert set_photo.status_code == 200, set_photo.text

    hidden = client.get(f"/files/{file_id}/url", headers=world.headers(client, "fin"))
    assert hidden.status_code == 404, hidden.text
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "hr")).status_code == 200
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "far")).status_code == 200
