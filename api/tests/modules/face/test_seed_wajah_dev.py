"""Penjaga skrip seed wajah palsu: hanya DB dev lokal."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "seed-wajah-dev.py"


def _load():
    spec = importlib.util.spec_from_file_location("seed_wajah_dev", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://vms:x@localhost:55433/vms_dev",
    "postgresql+asyncpg://vms:x@127.0.0.1:55433/vms_dev",
])
def test_local_database_is_accepted(url):
    assert _load().db_host_is_local(url) is True


@pytest.mark.parametrize("url", [
    "postgresql+asyncpg://vms:x@db.visiontech.id:5432/vms",
    "postgresql+asyncpg://vms:x@192.168.88.10:5432/vms",
])
def test_remote_database_is_refused(url):
    assert _load().db_host_is_local(url) is False
