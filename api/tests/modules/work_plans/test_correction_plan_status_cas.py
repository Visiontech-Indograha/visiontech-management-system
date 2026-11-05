"""Keputusan koreksi laporan tidak menimpa status jadwal yang diubah pihak lain (compare-and-set)."""
from __future__ import annotations

from tests.concurrency import tahan_lalu_ubah
from tests.conftest import World, requires_db
from tests.modules.work_plans.test_daily_corrections import _ask, _completed_plan, _decide, _plan_status, _report

pytestmark = requires_db


def test_setujui_koreksi_saat_jadwal_berubah_dapat_409_dan_tidak_menimpa(client, world: World):
    plan_id = _completed_plan(world)
    _report(client, world, plan_id)
    cid = _ask(client, world, plan_id).json()["correction_id"]
    hasil = tahan_lalu_ubah(
        "UPDATE work_plan_daily SET status = 'SUBMITTED' WHERE daily_plan_id = %s", (plan_id,),
        lambda: _decide(client, world, cid, "APPROVE"),
    )
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    assert _plan_status(plan_id) == "SUBMITTED"
