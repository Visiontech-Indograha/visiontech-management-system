"""
F-03 · Idempotency-Key opsional pada endpoint pengajuan (lembur sebagai contoh jalur utama).

  - Tanpa header: perilaku lama, tidak ada yang disimpan.
  - Key sama + isi sama → respons tersimpan (status dan badan sama), tidak ada baris ganda.
  - Key sama + isi beda → 422.
  - Format key tidak valid → 422.
  - Key dipakai pengguna lain → tidak bertabrakan (cakupan per pengguna).
  - Dua request paralel dengan key sama → hanya satu pengajuan tercipta; yang kalah memakai 409
    (sedang diproses) atau respons tersimpan, bukan galat duplikat.
  - Pembersihan: kunci lebih dari 7 hari dihapus.
"""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.database.session import AsyncSessionLocal
from app.shared.idempotency_repository import hapus_lebih_lama
from tests.conftest import World, requires_db, sync_query
from tests.daily import run_daily_to_ongoing

pytestmark = requires_db

_ALASAN = "Pengerjaan kabel tambahan"


def _body(plan_id: str, reason: str = _ALASAN) -> dict[str, object]:
    return {"daily_plan_id": plan_id, "hours": 2, "reason": reason}


def _post(client, headers: dict[str, str], body: dict[str, object]):
    return client.post("/overtime", headers=headers, json=body)


def _keyed(client, world: World, who: str, key: str) -> dict[str, str]:
    return {**world.headers(client, who), "Idempotency-Key": key}


def _rows_for(plan_id: str, employee_id: str) -> int:
    return sync_query(
        "SELECT count(*) FROM overtime WHERE daily_plan_id = %s AND employee_id = %s",
        (plan_id, employee_id),
    )[0][0]


def test_without_header_behaves_as_before(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    response = _post(client, world.headers(client, "member"), _body(plan_id))
    assert response.status_code == 201, response.text
    # Tanpa header tidak ada kunci yang disimpan untuk pengajuan ini.
    assert sync_query(
        "SELECT count(*) FROM idempotency_keys WHERE response_body->>'daily_plan_id' = %s", (plan_id,)
    )[0][0] == 0


def test_same_key_same_body_replays_stored_response(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    key = str(uuid.uuid4())
    headers = _keyed(client, world, "member", key)

    first = _post(client, headers, _body(plan_id))
    second = _post(client, headers, _body(plan_id))

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json() == first.json()
    assert _rows_for(plan_id, world.employees["member"]) == 1


def test_same_key_different_body_is_422(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    key = str(uuid.uuid4())
    headers = _keyed(client, world, "member", key)

    assert _post(client, headers, _body(plan_id)).status_code == 201
    response = _post(client, headers, _body(plan_id, reason="Alasan lain yang berbeda"))

    assert response.status_code == 422, response.text
    assert "IDEMPOTENCY_KUNCI_DIPAKAI" in response.text
    assert _rows_for(plan_id, world.employees["member"]) == 1


@pytest.mark.parametrize("key", ["pendek", "ada spasi di kunci", "x" * 129, "karakter!tidak#valid"])
def test_invalid_key_format_is_422(client, world: World, key: str):
    plan_id = run_daily_to_ongoing(world)
    response = _post(client, _keyed(client, world, "member", key), _body(plan_id))
    assert response.status_code == 422, response.text
    assert "IDEMPOTENCY_KUNCI_TIDAK_VALID" in response.text


def test_same_key_is_scoped_per_user(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    key = str(uuid.uuid4())

    leader = _post(client, _keyed(client, world, "leader", key), _body(plan_id))
    member = _post(client, _keyed(client, world, "member", key), _body(plan_id))

    assert leader.status_code == 201, leader.text
    assert member.status_code == 201, member.text
    assert leader.json()["employee_id"] == world.employees["leader"]
    assert member.json()["employee_id"] == world.employees["member"]


def test_parallel_same_key_creates_one_overtime(client, world: World):
    """Dua request paralel, key sama: satu pengajuan saja. Yang kalah = 409 sedang diproses,
    atau respons tersimpan yang identik. Bukan galat duplikat (409 tanpa kode idempotensi)."""
    plan_id = run_daily_to_ongoing(world)
    key = str(uuid.uuid4())
    headers = _keyed(client, world, "member", key)   # login dilakukan sebelum paralel

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_post, client, headers, _body(plan_id)) for _ in range(2)]
        responses = [f.result() for f in futures]

    assert _rows_for(plan_id, world.employees["member"]) == 1
    created = [r for r in responses if r.status_code == 201]
    assert created, [r.text for r in responses]
    assert all(r.status_code in (201, 409) for r in responses), [r.status_code for r in responses]
    for r in responses:
        if r.status_code == 201:
            assert r.json() == created[0].json()
        else:
            assert "IDEMPOTENCY_SEDANG_DIPROSES" in r.text


def test_cleanup_removes_keys_older_than_seven_days(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    key = str(uuid.uuid4())
    assert _post(client, _keyed(client, world, "member", key), _body(plan_id)).status_code == 201
    sync_query("UPDATE idempotency_keys SET created_at = now() - interval '8 days' WHERE key = %s", (key,))

    async def _jalankan() -> int:
        async with AsyncSessionLocal() as session, session.begin():
            return await hapus_lebih_lama(session, 7)

    assert asyncio.run(_jalankan()) >= 1
    assert sync_query("SELECT count(*) FROM idempotency_keys WHERE key = %s", (key,))[0][0] == 0
