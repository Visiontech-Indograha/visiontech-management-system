"""Uji aturan duplikat nama lokasi kerja (R-A0-06c)."""
from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


def test_duplicate_office_name_rejected(client, world):
    ops = world.headers(client, "ops")
    name = f"Kantor Kembar {world.tag}"
    body1 = {
        "name": name,
        "address": "Jl. A 1",
        "location": {"lat": -6.2, "lng": 106.8},
        "radius_m": 150,
    }
    r1 = client.post("/offices", headers=ops, json=body1)
    assert r1.status_code == 201, r1.text

    # Buat kantor lain dengan nama sama (atau variasi case/whitespace)
    body2 = {
        "name": f"  {name.lower()}  ",
        "address": "Jl. B 2",
        "location": {"lat": -6.3, "lng": 106.9},
        "radius_m": 100,
    }
    r2 = client.post("/offices", headers=ops, json=body2)
    assert r2.status_code == 409, r2.text
    assert r2.json()["error"]["code"] == "DUPLICATE_SITE_NAME"

    # Buat kantor ketiga untuk uji update
    body3 = {
        "name": f"Kantor Lain {world.tag}",
        "address": "Jl. C 3",
        "location": {"lat": -6.4, "lng": 107.0},
        "radius_m": 100,
    }
    r3 = client.post("/offices", headers=ops, json=body3)
    assert r3.status_code == 201, r3.text
    oid3 = r3.json()["id"]

    # Ubah kantor ketiga menjadi sama dengan kantor pertama (harus ditolak 409)
    r4 = client.put(f"/offices/{oid3}", headers=ops, json={"name": name})
    assert r4.status_code == 409, r4.text
    assert r4.json()["error"]["code"] == "DUPLICATE_SITE_NAME"

    # Ubah dengan namanya sendiri (harus berhasil 200)
    r5 = client.put(
        f"/offices/{oid3}",
        headers=ops,
        json={"name": f"Kantor Lain {world.tag}"},
    )
    assert r5.status_code == 200, r5.text
