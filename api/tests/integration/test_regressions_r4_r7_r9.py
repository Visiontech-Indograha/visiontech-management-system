"""
V-13 · Regresi wajib tersisa (dok 07 §3).
- R4: dokumen terbit tidak berubah — setiap kolom isi `plan_document` ditolak saat UPDATE; yang boleh
  berubah hanya siklusnya (status) dan pencatatan penerimaan, sekali tulis.
- R7: bentrok personel benar-benar ditandai.
- R9 (siklus aset) dipindah ke tests/modules/assets/test_asset_loans.py — alur V2 serah terima/pengembalian.
"""
from __future__ import annotations

from datetime import timedelta

import psycopg2
import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.modules.work_plans.test_flow_plans import create_draft_plan, run_plan_to_accepted, run_plan_to_in_progress

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
        world.add_person("other_leader", None)  # R-26: ketua harus staf lapangan
        params = (create_draft_plan(client, world, start_offset_days=30, leader="other_leader")[0],)
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
