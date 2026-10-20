"""
vms.new_id() — kunci utama seluruh tabel. Wajib UUIDv7 (P0-2): berurutan waktu agar indeks
dan partisi tetap rapat. PostgreSQL 16 belum punya uuidv7(), jadi dibuat sendiri di SQL.
"""
from __future__ import annotations

import time
import uuid

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def test_new_id_is_uuid_version_7_rfc_variant():
    ids = [uuid.UUID(str(v)) for (v,) in sync_query("SELECT vms.new_id() FROM generate_series(1, 50)")]

    assert all(i.version == 7 for i in ids)
    assert all(i.variant == uuid.RFC_4122 for i in ids)
    assert len(set(ids)) == 50


def test_new_id_embeds_current_unix_milliseconds():
    before = int(time.time() * 1000)
    (value,) = sync_query("SELECT vms.new_id()")[0]
    after = int(time.time() * 1000)

    embedded_ms = int(uuid.UUID(str(value)).hex[:12], 16)

    # Toleransi selisih jam laptop ↔ server.
    assert before - 120_000 <= embedded_ms <= after + 120_000


def test_new_id_is_time_ordered():
    (first,) = sync_query("SELECT vms.new_id()")[0]
    time.sleep(0.01)
    (second,) = sync_query("SELECT vms.new_id()")[0]

    assert str(first) < str(second)
