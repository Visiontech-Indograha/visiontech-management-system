"""
T-01 · Konteks RLS & audit per permintaan (dok 12: satu permintaan = satu transaksi + SET LOCAL).
Nilai harus terbaca fungsi DB, dan hilang begitu transaksinya selesai (R-08: tidak bocor
ke permintaan lain yang memakai koneksi yang sama).
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.db.context import set_request_context
from app.db.session import make_engine
from tests.conftest import requires_db

pytestmark = requires_db


def test_context_is_visible_inside_transaction_and_gone_after():
    user_id, org_id = uuid.uuid4(), uuid.uuid4()

    async def run() -> tuple[tuple, tuple]:
        engine = make_engine(poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                async with conn.begin():
                    await set_request_context(conn, user_id=str(user_id), organization_id=str(org_id),
                                              actor_label="uji@contoh.test")
                    inside = (await conn.execute(text(
                        "SELECT vms.current_user_id(), vms.current_org_id(), current_setting('app.actor_label', true)"
                    ))).one()
                after = (await conn.execute(text(
                    "SELECT vms.current_user_id(), vms.current_org_id(), current_setting('app.actor_label', true)"
                ))).one()
                await conn.rollback()
                return tuple(inside), tuple(after)
        finally:
            await engine.dispose()

    inside, after = asyncio.run(run())

    assert inside == (user_id, org_id, "uji@contoh.test")
    assert after[0] is None and after[1] is None and not after[2]


def test_protected_endpoint_reaches_database(client, seeded_user):
    """Sebelum T-01, setiap endpoint ber-`get_db_with_user` berakhir 500."""
    access = client.post(
        "/auth/login", json={"email": seeded_user.login, "password": seeded_user.password}
    ).json()["access_token"]

    response = client.get("/sites", headers={"Authorization": f"Bearer {access}"})

    assert response.status_code != 500, response.text
