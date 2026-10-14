"""
R-20 · M2-01 — data kontak pribadi (email, telepon, alamat, tanggal lahir, kontak darurat) hanya
untuk pemiliknya dan HR/admin (prototipe `privateAccess`, dok 08 ancaman "mengintip data rekan").
Dulu setiap akun (izin dasar view:users) membaca semuanya lewat direktori.
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

PRIVATE = ("email", "phone", "address", "birth_date")


def _fill(world: World, who: str) -> str:
    emp = world.employees[who]
    sync_query("UPDATE vms.employee SET phone = '0812', address = 'Jl. Uji 1', birth_date = '1990-01-02', "
               "email = 'uji@contoh.id' WHERE id = %s RETURNING id", (emp,))
    return emp


def _detail(client, world: World, who: str, emp: str) -> dict:
    r = client.get(f"/employees/{emp}", headers=world.headers(client, who))
    assert r.status_code == 200, r.text
    return r.json()


def _listed(client, world: World, who: str, emp: str) -> dict:
    r = client.get("/employees", headers=world.headers(client, who), params={"size": 100})
    assert r.status_code == 200, r.text
    return next(e for e in r.json()["items"] if e["id"] == emp)


def test_colleague_sees_no_private_fields(client, world: World):
    emp = _fill(world, "member")
    for view in (_detail(client, world, "leader", emp), _listed(client, world, "leader", emp)):
        assert all(view[f] is None for f in PRIVATE), view
        assert view["full_name"] and view["position"] is not None   # data kerja tetap terlihat


def test_owner_and_hr_see_private_fields(client, world: World):
    emp = _fill(world, "member")
    for who in ("member", "hr", "admin"):
        view = _detail(client, world, who, emp)
        assert (view["phone"], view["address"]) == ("0812", "Jl. Uji 1"), who
        assert _listed(client, world, who, emp)["phone"] == "0812", who
