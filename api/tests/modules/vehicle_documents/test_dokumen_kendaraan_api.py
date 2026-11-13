"""API dokumen kendaraan: matriks peran, riwayat (diganti), kantor lain, pengemudi, /mine."""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


@pytest.fixture
def siap(world: World, other_world: World) -> tuple[World, str]:
    world.add_person("hse", "HSE")
    other_world.add_person("hse", "HSE")
    vid = str(sync_query(
        "INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate) "
        "VALUES (%s, %s, 'Car', 'Mobil uji', %s) RETURNING vehicle_id",
        (world.org_id, world.unit_id, f"UJ{uuid.uuid4().hex[:8].upper()}"))[0][0])
    return world, vid


def _body(tipe: str = "STNK", hari: int = 20) -> dict[str, Any]:
    jatuh = (jakarta_now().date() + timedelta(days=hari)).isoformat()
    return {"doc_type_code": tipe, "doc_no": "NO-1", "expired_on": jatuh}


def test_matriks_peran_tulis_dan_lihat(client: Any, siap: tuple[World, str]) -> None:
    w, vid = siap
    for who, kode in (("hse", 201), ("ops", 201), ("admin", 201), ("hr", 403), ("pm", 403), ("member", 403)):
        r = client.post(f"/vehicles/{vid}/documents", json=_body(), headers=w.headers(client, who))
        assert r.status_code == kode, who
    for who, kode in (("hse", 200), ("ops", 200), ("hr", 403), ("member", 403), ("leader", 403)):
        assert client.get("/vehicle-documents", headers=w.headers(client, who)).status_code == kode, who
        assert client.get("/vehicle-documents/expiring", headers=w.headers(client, who)).status_code == kode, who


def test_dokumen_baru_menandai_lama_diganti(client: Any, siap: tuple[World, str]) -> None:
    w, vid = siap
    h = w.headers(client, "hse")
    assert client.post(f"/vehicles/{vid}/documents", json=_body("KIR", 10), headers=h).status_code == 201
    assert client.post(f"/vehicles/{vid}/documents", json=_body("KIR", 300), headers=h).status_code == 201
    aktif = client.get("/vehicle-documents", params={"vehicle_id": vid}, headers=h).json()
    assert [d["status"] for d in aktif] == ["active"]
    semua = client.get("/vehicle-documents", params={"vehicle_id": vid, "history": True}, headers=h)
    assert sorted(d["status"] for d in semua.json()) == ["active", "replaced"]
    jatuh = client.get("/vehicle-documents/expiring", params={"days": 30}, headers=h).json()
    assert [d for d in jatuh if d["vehicle_id"] == vid] == []  # yang lama sudah diganti


def test_expiring_paginasi_dan_validasi(client: Any, siap: tuple[World, str]) -> None:
    w, vid = siap
    h = w.headers(client, "hse")
    client.post(f"/vehicles/{vid}/documents", json=_body("STNK", 5), headers=h)
    client.post(f"/vehicles/{vid}/documents", json=_body("PAJAK", 40), headers=h)
    r = client.get("/vehicle-documents/expiring", params={"days": 30, "page": 1, "size": 10}, headers=h)
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "1" and r.json()[0]["doc_type_code"] == "STNK"
    assert client.get("/vehicle-documents/expiring", params={"days": 500}, headers=h).status_code == 422
    assert client.post(f"/vehicles/{vid}/documents", json=_body("TIDAK_ADA"), headers=h).status_code == 422
    salah = {**_body(), "issued_on": (jakarta_now().date() + timedelta(days=99)).isoformat()}
    assert client.post(f"/vehicles/{vid}/documents", json=salah, headers=h).status_code == 422


def test_kantor_lain_dijawab_404(client: Any, siap: tuple[World, str], other_world: World) -> None:
    w, vid = siap
    asing = other_world.headers(client, "hse")
    assert client.post(f"/vehicles/{vid}/documents", json=_body(), headers=asing).status_code == 404
    assert client.get("/vehicle-documents", params={"vehicle_id": vid}, headers=asing).status_code == 404
    client.post(f"/vehicles/{vid}/documents", json=_body(), headers=w.headers(client, "hse"))
    assert client.get("/vehicle-documents", headers=asing).json() == []


def test_pengemudi_dan_mine(client: Any, siap: tuple[World, str]) -> None:
    w, vid = siap
    h = w.headers(client, "hse")
    client.post(f"/vehicles/{vid}/documents", json=_body(), headers=h)
    m = w.headers(client, "member")
    assert client.get("/vehicle-documents/mine", headers=m).json() == []
    r = client.post(f"/vehicles/{vid}/drivers", json={"employee_id": w.employees["member"]}, headers=h)
    assert r.status_code == 201
    dup = client.post(f"/vehicles/{vid}/drivers", json={"employee_id": w.employees["member"]}, headers=h)
    assert dup.status_code == 409
    assert len(client.get("/vehicle-documents/mine", headers=m).json()) == 1
    assert client.get("/vehicle-documents/mine", headers=w.headers(client, "leader")).json() == []
    tolak = client.post(f"/vehicles/{vid}/drivers", json={"employee_id": w.employees["leader"]}, headers=m)
    assert tolak.status_code == 403
    did = r.json()[0]["vehicle_driver_id"]
    assert client.post(f"/vehicles/{vid}/drivers/{did}/end", headers=h).status_code == 200
    assert client.get("/vehicle-documents/mine", headers=m).json() == []
    assert client.post(f"/vehicles/{vid}/drivers/{did}/end", headers=h).status_code == 404
