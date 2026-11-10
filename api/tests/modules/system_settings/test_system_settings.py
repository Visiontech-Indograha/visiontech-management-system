"""Setelan sistem: hanya SUPER_ADMIN, validasi tipe/kunci, audit sebelum/sesudah, urutan prioritas, cache.

DB uji dipakai bersama tes lain, jadi tes memakai kunci uji `TEST_FLAG` (didaftarkan sementara di SPECS) agar
tidak mengubah ROLE_ASSIGNMENT_ENABLED/RATE_LIMIT_ENFORCE milik tes yang berjalan paralel.
"""
from __future__ import annotations

import uuid

import pytest

from app.core import system_settings
from app.core.config import settings
from tests.conftest import login_headers, requires_db, sync_query

pytestmark = requires_db

KEY = "TEST_FLAG_" + uuid.uuid4().hex[:8]  # unik per proses xdist: worker lain tidak saling mengganggu


@pytest.fixture(autouse=True)
def _test_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(
        system_settings.SPECS, KEY, system_settings.SettingSpec(KEY, "Bendera uji", "Hanya untuk tes.", None),
    )
    _clean()
    yield
    _clean()


def _clean() -> None:
    sync_query("DELETE FROM system_setting WHERE key = %s", (KEY,))
    sync_query("DELETE FROM app_activity_logs WHERE action = 'SYSTEM_SETTING_UPDATE' AND changed_diff->>'key' = %s",
               (KEY,))
    system_settings.reset_cache()


def _by_key(response) -> dict:
    return {r["key"]: r for r in response.json()}


def test_only_super_admin(client, make_user):
    for role in ("ADMIN_HR_GA", "OPERATIONAL_MANAGER", "FINANCE", "PROJECT_MANAGER", "HSE", None):
        h = login_headers(client, make_user(role))
        assert client.get("/system/settings", headers=h).status_code == 403, role
        assert client.put("/system/settings", headers=h, json={"values": {KEY: True}}).status_code == 403, role
    assert client.get("/system/settings").status_code == 401


def test_default_comes_from_env_then_db_row_wins_and_is_audited(client, make_user):
    h = login_headers(client, make_user("SUPER_ADMIN"))
    row = _by_key(client.get("/system/settings", headers=h))[KEY]
    assert (row["value"], row["source"], row["env_default"], row["locked"]) == (False, "env_default", False, False)

    r = client.put("/system/settings", headers=h, json={"values": {KEY: True}})
    assert r.status_code == 200, r.text
    row = _by_key(r)[KEY]
    assert (row["value"], row["source"]) == (True, "db")
    assert system_settings.get_bool(KEY) is True  # cache proses ini langsung segar
    assert sync_query("SELECT value::text FROM system_setting WHERE key = %s", (KEY,)) == [("true",)]

    audit = sync_query(
        "SELECT changed_diff->>'before', changed_diff->>'after' FROM app_activity_logs "
        "WHERE action = 'SYSTEM_SETTING_UPDATE' AND changed_diff->>'key' = %s ORDER BY created_at DESC LIMIT 1",
        (KEY,),
    )
    assert audit == [("false", "true")]

    same = client.put("/system/settings", headers=h, json={"values": {KEY: True}})
    assert same.status_code == 200  # tanpa perubahan: tanpa audit baru
    n = sync_query("SELECT count(*) FROM app_activity_logs WHERE action = 'SYSTEM_SETTING_UPDATE' "
                   "AND changed_diff->>'key' = %s", (KEY,))
    assert n == [(1,)]


def test_validation_unknown_key_and_non_boolean(client, make_user):
    h = login_headers(client, make_user("SUPER_ADMIN"))
    assert client.put("/system/settings", headers=h, json={"values": {"NGAWUR": True}}).status_code == 422
    assert client.put("/system/settings", headers=h, json={"values": {KEY: "true"}}).status_code == 422
    assert client.put("/system/settings", headers=h, json={"values": {KEY: 1}}).status_code == 422
    assert client.put("/system/settings", headers=h, json={"values": {}}).status_code == 422
    assert sync_query("SELECT 1 FROM system_setting WHERE key = %s", (KEY,)) == []


def test_env_force_has_highest_priority_and_locks(client, make_user, monkeypatch):
    h = login_headers(client, make_user("SUPER_ADMIN"))
    client.put("/system/settings", headers=h, json={"values": {KEY: True}})
    monkeypatch.setattr(settings, "SYSTEM_SETTINGS_FORCE", f"{KEY}=false")
    row = _by_key(client.get("/system/settings", headers=h))[KEY]
    assert (row["value"], row["source"], row["locked"]) == (False, "env_force", True)
    r = client.put("/system/settings", headers=h, json={"values": {KEY: True}})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SETTING_LOCKED"


def test_cache_refreshes_from_database_for_other_processes(client, make_user):
    import asyncio

    from app.database.session import AsyncSessionLocal

    sync_query("INSERT INTO system_setting (key, value) VALUES (%s, 'true'::jsonb)", (KEY,))

    async def go() -> None:
        async with AsyncSessionLocal() as db:
            await system_settings.refresh(db)

    assert system_settings.get_bool(KEY) is False  # cache lama
    asyncio.run(go())
    assert system_settings.get_bool(KEY) is True


def test_real_flags_follow_env_when_no_row(monkeypatch):
    saved = dict(system_settings._cache)
    system_settings.reset_cache()
    try:
        monkeypatch.setattr(settings, "SYSTEM_SETTINGS_FORCE", "")
        monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
        assert system_settings.role_assignment_enabled() is True
        monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)
        assert system_settings.role_assignment_enabled() is False
        monkeypatch.setattr(settings, "SYSTEM_SETTINGS_FORCE", "ROLE_ASSIGNMENT_ENABLED=true, RATE_LIMIT_ENFORCE=salah")
        assert system_settings.role_assignment_enabled() is True  # override darurat menang
        assert system_settings.source_of("RATE_LIMIT_ENFORCE") == "env_default"  # nilai tak valid diabaikan
    finally:
        system_settings.set_cached(saved)
