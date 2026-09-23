"""T-05 · `create-admin` membuat pengguna ber-peran `ADMIN` yang benar-benar bisa login."""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.cli import CliError, create_admin
from tests.conftest import requires_db, sync_query

pytestmark = requires_db


@pytest.fixture
def org_id():
    (value,) = sync_query("INSERT INTO vms.organization (name) VALUES ('Organisasi uji CLI') RETURNING id")[0]
    yield str(value)
    sync_query("DELETE FROM vms.organization WHERE id = %s", (value,))


def test_create_admin_stores_admin_role_and_can_log_in(client, org_id):
    login = f"admin-{uuid.uuid4().hex[:10]}@contoh.test"

    asyncio.run(create_admin(login, "KataSandiAdmin-123", organization_id=org_id))

    roles = sync_query(
        "SELECT r.role::text FROM vms.user_role r JOIN vms.app_user u ON u.id = r.user_id WHERE u.login = %s",
        (login,),
    )
    assert roles == [("ADMIN",)]
    response = client.post("/auth/login", json={"email": login, "password": "KataSandiAdmin-123"})
    assert response.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"}).json()
    assert "manage:users" in me["permissions"]
    sync_query("DELETE FROM vms.login_attempt WHERE login = %s", (login,))


def test_create_admin_refuses_existing_login(org_id):
    login = f"admin-{uuid.uuid4().hex[:10]}@contoh.test"
    asyncio.run(create_admin(login, "KataSandiAdmin-123", organization_id=org_id))

    with pytest.raises(CliError, match="sudah ada"):
        asyncio.run(create_admin(login, "LainLagi-456", organization_id=org_id))


def test_create_admin_rejects_unknown_organization():
    with pytest.raises(CliError, match="Organisasi"):
        asyncio.run(create_admin("x@contoh.test", "KataSandiAdmin-123", organization_id=str(uuid.uuid4())))


def test_create_admin_rejects_short_password(org_id):
    with pytest.raises(CliError, match="minimal"):
        asyncio.run(create_admin("y@contoh.test", "pendek", organization_id=org_id))
