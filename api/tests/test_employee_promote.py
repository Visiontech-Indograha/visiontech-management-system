"""
R-19 · Mutasi/promosi karyawan (domain.js PROMOTE, M2) + riwayat penempatan + daftar unit.
- Karyawan harus aktif; jabatan wajib; unit milik organisasi (kosong = unit tetap, dulu dikosongkan).
- Mutasi LINTAS unit diblokir selama masih bertugas di SK aktif; promosi di unit yang sama boleh.
- Tanggal berlaku tidak boleh sebelum penempatan terakhir (dulu CHECK DB → 500).
- GET /employees/{id}/assignments (view:users, organisasi sendiri) · GET /units (organisasi sendiri).
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_accepted

pytestmark = requires_db


def _promote(client, world: World, who: str, **body):
    return client.post(f"/employees/{world.employees[who]}/assignments", headers=world.headers(client, "hr"),
                       json={"position": "Supervisor", "valid_from": "2026-09-01", **body})


def _unit_of(world: World, who: str) -> str | None:
    row = sync_query("SELECT unit_id::text FROM vms.employee WHERE id = %s", (world.employees[who],))
    return row[0][0]


def test_promotion_keeps_the_unit_when_none_is_given_and_is_listed_in_history(client, world):
    before = _unit_of(world, "member")
    promoted = _promote(client, world, "member")
    assert promoted.status_code == 200, promoted.text
    assert _unit_of(world, "member") == before                       # dulu: unit dikosongkan
    assert sync_query("SELECT position FROM vms.employee WHERE id = %s", (world.employees["member"],)) \
        == [("Supervisor",)]

    history = client.get(f"/employees/{world.employees['member']}/assignments", headers=world.headers(client, "hr"))
    assert history.status_code == 200, history.text
    rows = history.json()
    assert rows[0]["position"] == "Supervisor" and rows[0]["valid_to"] is None
    assert (rows[0]["unit_id"], rows[0]["unit_name"]) == (before, "CCTV & ACS")
    assert all(r["valid_to"] is not None for r in rows[1:])


def test_cross_unit_move_is_blocked_while_on_an_active_plan(client, world):
    run_plan_to_accepted(client, world)                              # member bertugas di SK ACCEPTED
    other_unit = world.add_unit("WALLD")

    blocked = _promote(client, world, "member", unit_id=other_unit)
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["message"] == "Mutasi lintas unit diblokir sampai penugasan aktif diserahterimakan."

    same_unit = _promote(client, world, "member", position="Teknisi Senior")   # promosi di unit sama boleh
    assert same_unit.status_code == 200, same_unit.text


def test_inactive_employee_and_bad_dates_are_rejected(client, world):
    assert _promote(client, world, "member").status_code == 200                         # penempatan 2026-09-01
    earlier = _promote(client, world, "member", valid_from="2026-08-01")
    assert earlier.status_code == 422, earlier.text   # sebelum penempatan terakhir (dulu CHECK DB → 500)
    assert _promote(client, world, "member", position="  ").status_code == 422
    sync_query("UPDATE vms.employee SET is_active = false WHERE id = %s", (world.employees["member"],))
    inactive = _promote(client, world, "member")
    assert inactive.status_code == 409 and inactive.json()["error"]["message"] == "Karyawan harus aktif."


def test_units_list_is_scoped_to_own_organisation(client, world, other_world):
    world.add_unit("WALLD")
    units = client.get("/units", headers=world.headers(client, "member"))
    assert units.status_code == 200, units.text
    codes = {u["code"] for u in units.json()}
    assert "WALLD" in codes
    foreign = {u["id"] for u in client.get("/units", headers=other_world.headers(client, "member")).json()}
    assert not foreign & {u["id"] for u in units.json()}


def test_history_follows_directory_visibility(client, world, other_world):
    """Direktori terbuka untuk organisasi sendiri (view:users); organisasi lain → 404."""
    path = f"/employees/{world.employees['member']}/assignments"
    assert client.get(path, headers=world.headers(client, "finance")).status_code == 200
    assert client.get(path, headers=other_world.headers(client, "hr")).status_code == 404
