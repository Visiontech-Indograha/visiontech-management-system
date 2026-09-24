"""
V-13 · Regresi wajib tersisa (dok 07 §3).
- R4: dokumen terbit tidak berubah — setiap kolom isi `plan_document` ditolak saat UPDATE; yang boleh
  berubah hanya siklusnya (status) dan pencatatan penerimaan, sekali tulis.
- R7: bentrok personel benar-benar ditandai.
- R9: siklus aset pesan → kembali → (tolak → kembali lagi) → verifikasi selesai tanpa jalan buntu.
"""
from __future__ import annotations

from datetime import timedelta

import psycopg2
import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_accepted, run_plan_to_in_progress

pytestmark = requires_db

IMMUTABLE = "Dokumen terbit bersifat tetap. Terbitkan versi baru, jangan mengubah versi lama."


# ── R4 ────────────────────────────────────────────────────────────────────────────────────────
def _update_document(world: World, doc_id: str, assignment: str, params: tuple = ()) -> None:
    sync_query(
        f"WITH _ctx AS (SELECT set_config('app.organization_id', %s, true)) "
        f"UPDATE vms.plan_document SET {assignment} FROM _ctx WHERE id = %s",
        (world.org_id, *params, doc_id))


@pytest.mark.parametrize(("column", "assignment"), [
    ("snapshot", "snapshot = '{\"dipalsukan\": true}'::jsonb"),
    ("snapshot_sha256", "snapshot_sha256 = digest('palsu', 'sha256')"),   # dipakai verifikasi QR
    ("number", "number = 'SK-PALSU'"),
    ("version", "version = version + 10"),
    ("kind", "kind = 'REVISION'"),
    ("reason", "reason = 'alasan diganti'"),
    ("issued_by", "issued_by = accepted_by"),
    ("issued_at", "issued_at = issued_at - interval '1 day'"),
    ("work_plan_id", "work_plan_id = %s"),                                   # dipindah ke SK lain
    ("accepted_by", "accepted_by = issued_by"),                              # penerimaan sekali tulis
    ("accepted_at", "accepted_at = accepted_at - interval '1 day'"),
])
def test_r4_published_document_content_cannot_be_updated(client, world, column, assignment):
    plan_id, _ = run_plan_to_accepted(client, world)
    params: tuple = ()
    if column == "work_plan_id":   # SK lain di organisasi yang sama, tanpa bentrok jadwal
        params = (create_draft_plan(client, world, start_offset_days=30, leader="ops")[0],)
    doc_id, before = sync_query(f"SELECT id::text, {column}::text FROM vms.plan_document WHERE work_plan_id = %s",
                                (plan_id,))[0]

    with pytest.raises(psycopg2.Error) as raised:
        _update_document(world, doc_id, assignment, params)

    assert IMMUTABLE in str(raised.value)
    assert sync_query(f"SELECT {column}::text FROM vms.plan_document WHERE id = %s", (doc_id,)) == [(before,)]


def test_r4_document_lifecycle_can_still_move_forward(client, world):
    """Status tetap boleh bergerak (mis. versi lama digantikan revisi) — hanya isinya yang terkunci."""
    plan_id, _ = run_plan_to_accepted(client, world)
    doc_id = sync_query("SELECT id::text FROM vms.plan_document WHERE work_plan_id = %s", (plan_id,))[0][0]

    _update_document(world, doc_id, "status = 'SUPERSEDED'")

    assert sync_query("SELECT status::text FROM vms.plan_document WHERE id = %s", (doc_id,)) == [("SUPERSEDED",)]


# ── R7 ────────────────────────────────────────────────────────────────────────────────────────
def test_r7_conflicting_member_is_flagged(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)          # anggota bertugas hari ini & besok
    number = sync_query("SELECT number FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]
    member, pm = world.employees["member"], world.headers(client, "pm")
    today = jakarta_now().date()

    def conflicts(start, end, exclude=None):
        params = {"start_date": start.isoformat(), "end_date": end.isoformat()}
        if exclude:
            params["exclude_plan"] = exclude
        response = client.get(f"/employees/{member}/conflicts", headers=pm, params=params)
        assert response.status_code == 200, response.text
        return response.json()

    overlapping = conflicts(today + timedelta(days=1), today + timedelta(days=5))
    assert overlapping["has_conflict"] is True
    assert overlapping["conflicts"] == [{"id": plan_id, "number": number, "title": "Instalasi CCTV gudang"}]
    assert conflicts(today + timedelta(days=30), today + timedelta(days=31))["has_conflict"] is False
    assert conflicts(today, today + timedelta(days=5), exclude=plan_id)["has_conflict"] is False


# ── R9 ────────────────────────────────────────────────────────────────────────────────────────
def test_r9_asset_cycle_has_no_dead_end(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer, leader = world.headers(client, "asset"), world.headers(client, "leader")
    asset = client.post("/assets", headers=officer,
                        json={"kind": "TOOL", "code": "TL-R9", "name": "Tangga lipat", "condition": "BAIK"})
    asset_id = asset.json()["id"]

    def allocate():
        return client.post("/assets/allocate", headers=officer, json={"asset_id": asset_id, "work_plan_id": plan_id})

    def request_return():
        return client.post(f"/assets/allocations/{alloc_id}/return", headers=leader,
                           json={"condition_on_return": "BAIK", "note": "Selesai dipakai"})

    def verify(return_id, accepted, note):
        return client.post(f"/assets/returns/{return_id}/verify", headers=officer,
                           json={"is_accepted": accepted, "note": note})

    def asset_status():
        return sync_query("SELECT status::text FROM vms.asset WHERE id = %s", (asset_id,))[0][0]

    allocated = allocate()
    assert allocated.status_code == 200, allocated.text
    alloc_id = allocated.json()["id"]

    first = request_return()
    assert first.status_code == 200, first.text
    assert asset_status() == "RETURN_PENDING"
    duplicate = request_return()
    assert duplicate.status_code == 409 and duplicate.json()["error"]["message"] == \
        "Aset belum dipinjam atau sudah menunggu verifikasi."

    rejected = verify(first.json()["id"], False, "Anak tangga retak")
    assert rejected.status_code == 200, rejected.text
    assert asset_status() == "IN_USE"                                 # kembali ke tim, bukan buntu
    again = verify(first.json()["id"], True, "coba lagi")
    assert again.status_code == 409 and again.json()["error"]["message"] == \
        "Aset belum menunggu verifikasi pengembalian."

    second = request_return()
    assert second.status_code == 200, second.text
    accepted = verify(second.json()["id"], True, "Sudah diperbaiki")
    assert accepted.status_code == 200, accepted.text
    assert asset_status() == "AVAILABLE"
    assert sync_query("SELECT released_at IS NOT NULL FROM vms.asset_allocation WHERE id = %s", (alloc_id,)) \
        == [(True,)]
    assert request_return().status_code == 409                        # alokasi sudah dilepas

    reallocated = allocate()                                          # aset benar-benar bisa dipakai lagi
    assert reallocated.status_code == 200, reallocated.text


def test_asset_return_of_another_organisation_cannot_be_verified(client, world, other_world):
    """Jalur ber-id `return_id` dibatasi organisasi (celah V-09 yang tersisa)."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer = world.headers(client, "asset")
    asset_id = client.post("/assets", headers=officer, json={
        "kind": "TOOL", "code": "TL-ASING", "name": "Bor", "condition": "BAIK"}).json()["id"]
    alloc_id = client.post("/assets/allocate", headers=officer,
                           json={"asset_id": asset_id, "work_plan_id": plan_id}).json()["id"]
    return_id = client.post(f"/assets/allocations/{alloc_id}/return", headers=world.headers(client, "leader"),
                            json={"condition_on_return": "BAIK"}).json()["id"]

    response = client.post(f"/assets/returns/{return_id}/verify", headers=other_world.headers(client, "asset"),
                           json={"is_accepted": True, "note": "bukan milik saya"})

    assert response.status_code == 404, response.text
    assert sync_query("SELECT verified_at IS NULL FROM vms.asset_return WHERE id = %s", (return_id,)) == [(True,)]
