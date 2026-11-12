"""
T-01 · Konteks audit & RLS per permintaan (dok 12: satu permintaan = satu transaksi + SET LOCAL).
Nilai harus terbaca di DB (current_setting), dan hilang begitu transaksinya selesai (R-08: tidak bocor
ke permintaan lain yang memakai koneksi yang sama pada connection pool).
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.database.session import make_engine, set_request_context
from tests.conftest import requires_db

pytestmark = requires_db

_FULL_CONTEXT_SQL = (
    "SELECT NULLIF(current_setting('app.user_id', true), '')::uuid, "
    "NULLIF(current_setting('app.organization_id', true), '')::uuid, "
    "NULLIF(current_setting('app.org_id', true), '')::uuid, "
    "current_setting('app.actor_label', true), "
    "current_setting('app.role', true), "
    "NULLIF(current_setting('app.office_id', true), '')::uuid, "
    "NULLIF(current_setting('app.division_id', true), '')::uuid, "
    "current_setting('app.is_system', true)"
)


def test_context_is_visible_inside_transaction_and_gone_after():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    office_id = uuid.uuid4()
    division_id = uuid.uuid4()

    async def run() -> tuple[tuple, tuple]:
        engine = make_engine(poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                async with conn.begin():
                    await set_request_context(
                        conn,
                        user_id=str(user_id),
                        organization_id=str(org_id),
                        actor_label="uji@contoh.test",
                        role="PROJECT_MANAGER",
                        office_id=str(office_id),
                        division_id=str(division_id),
                        is_system=False,
                    )
                    inside = (await conn.execute(text(_FULL_CONTEXT_SQL))).one()
                after = (await conn.execute(text(_FULL_CONTEXT_SQL))).one()
                await conn.rollback()
                return tuple(inside), tuple(after)
        finally:
            await engine.dispose()

    inside, after = asyncio.run(run())

    assert inside == (
        user_id,
        org_id,
        org_id,
        "uji@contoh.test",
        "PROJECT_MANAGER",
        office_id,
        division_id,
        "0",
    )
    # Setelah transaksi selesai, seluruh variabel sesi harus bersih (tidak bocor)
    assert after[0] is None
    assert after[1] is None
    assert after[2] is None
    assert not after[3]
    assert not after[4]
    assert after[5] is None
    assert after[6] is None
    assert not after[7]


def test_context_does_not_leak_across_pooled_connections():
    """
    Memastikan koneksi pool yang dipakai ulang secara berurutan tidak membocorkan
    variabel sesi dari transaksi sebelumnya (B-07).
    """
    user_1, org_1, office_1 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    user_2, org_2, office_2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    async def run() -> None:
        # Engine dengan kapasitas pool 1 agar koneksi fisik dipastikan dipakai ulang
        engine = make_engine(pool_size=1, max_overflow=0)
        try:
            # 1. Transaksi pertama pada koneksi pool
            async with engine.connect() as conn1, conn1.begin():
                await set_request_context(
                    conn1,
                    user_id=str(user_1),
                    org_id=str(org_1),
                    actor_label="user1@contoh.test",
                    role="SUPER_ADMIN",
                    office_id=str(office_1),
                    is_system=True,
                )
                row1 = (await conn1.execute(text(_FULL_CONTEXT_SQL))).one()
                assert row1[0] == user_1
                assert row1[2] == org_1
                assert row1[4] == "SUPER_ADMIN"
                assert row1[7] == "1"

            # 2. Transaksi kedua pada koneksi yang dikembalikan ke pool:
            # SEBELUM set_request_context dipanggil, variabel sesi harus kosong
            async with engine.connect() as conn2, conn2.begin():
                row_before = (await conn2.execute(text(_FULL_CONTEXT_SQL))).one()
                assert row_before[0] is None, f"user_id bocor dari conn1: {row_before[0]}"
                assert row_before[1] is None, f"org_id bocor dari conn1: {row_before[1]}"
                assert row_before[2] is None
                assert not row_before[3]
                assert not row_before[4]
                assert row_before[5] is None
                assert not row_before[7]

                await set_request_context(
                    conn2,
                    user_id=str(user_2),
                    org_id=str(org_2),
                    actor_label="user2@contoh.test",
                    role="EMPLOYEE",
                    office_id=str(office_2),
                    is_system=False,
                )
                row2 = (await conn2.execute(text(_FULL_CONTEXT_SQL))).one()
                assert row2[0] == user_2
                assert row2[2] == org_2
                assert row2[4] == "EMPLOYEE"
                assert row2[7] == "0"
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_concurrent_transactions_maintain_isolated_contexts():
    """
    Memastikan dua transaksi yang berjalan bersamaan (konkuren) di pool
    mempertahankan konteks masing-masing tanpa saling menimpa (xdist aman).
    """
    user_a, org_a = uuid.uuid4(), uuid.uuid4()
    user_b, org_b = uuid.uuid4(), uuid.uuid4()

    async def worker(u_id: uuid.UUID, o_id: uuid.UUID, role_name: str, barrier: asyncio.Barrier, engine) -> tuple:
        async with engine.connect() as conn, conn.begin():
            await set_request_context(
                conn,
                user_id=str(u_id),
                org_id=str(o_id),
                actor_label=f"{role_name}@contoh.test",
                role=role_name,
            )
            await barrier.wait()  # Sinkronisasi agar kedua transaksi berada di dalam konteks aktif serentak
            row = (await conn.execute(text(_FULL_CONTEXT_SQL))).one()
            await barrier.wait()
            return tuple(row)

    async def run() -> tuple[tuple, tuple]:
        engine = make_engine(pool_size=5, max_overflow=5)
        barrier = asyncio.Barrier(2)
        try:
            res_a, res_b = await asyncio.gather(
                worker(user_a, org_a, "ROLE_A", barrier, engine),
                worker(user_b, org_b, "ROLE_B", barrier, engine),
            )
            return res_a, res_b
        finally:
            await engine.dispose()

    res_a, res_b = asyncio.run(run())
    assert res_a[0] == user_a and res_a[4] == "ROLE_A"
    assert res_b[0] == user_b and res_b[4] == "ROLE_B"


def test_protected_endpoint_reaches_database(client, seeded_user):
    """Sebelum T-01, setiap endpoint ber-`get_db_with_user` berakhir 500."""
    access = client.post(
        "/auth/login", json={"email": seeded_user.login, "password": seeded_user.password}
    ).json()["access_token"]

    response = client.get("/offices", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code != 500, response.text
