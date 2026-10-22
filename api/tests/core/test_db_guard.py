"""A-00 (docs/24): uji tidak boleh pernah berjalan terhadap DB produksi."""
from __future__ import annotations

import pytest

from tests.db_guard import unsafe_test_database, unsafe_test_storage


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://postgres:x@localhost:5432/visiontech_db",       # CI (layanan lokal)
    "postgresql+asyncpg://postgres:x@127.0.0.1:5432/vms",
    "postgresql+asyncpg://vms_app:x@100.117.92.14:5434/vms_test",         # DB uji server (T0)
    "postgresql+asyncpg://vms_app:x@192.168.88.160:5434/test_migration",  # DB uji Master Schema V2
])
def test_local_and_test_databases_are_allowed(url):
    assert unsafe_test_database(url) is None


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://vms_app:x@100.117.92.14:5433/visiontech_db",    # DB produksi (A-00)
    "postgresql+asyncpg://vms_app:x@visiontech-bar.tail827174.ts.net:5433/visiontech_db",
    "postgresql+asyncpg://vms_app:x@db.example.com:5432/vms",
])
def test_remote_non_test_databases_are_refused(url):
    reason = unsafe_test_database(url)
    assert reason is not None and "produksi" in reason


@pytest.mark.parametrize("endpoint", ["127.0.0.1:9000", "localhost:9000", "100.117.92.14:9100"])
def test_local_and_test_storage_is_allowed(endpoint):
    assert unsafe_test_storage(endpoint) is None


@pytest.mark.parametrize("endpoint", ["192.168.88.160:9000", "100.117.92.14:9000", "minio:9000"])
def test_production_storage_is_refused(endpoint):
    reason = unsafe_test_storage(endpoint)
    assert reason is not None and "produksi" in reason
