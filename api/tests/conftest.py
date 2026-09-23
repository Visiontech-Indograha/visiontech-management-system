"""
Fixture uji bersama. Uji integrasi memakai PostgreSQL sungguhan (dok 07, dok 12 §1),
bukan SQLite — separuh aturan hidup di fungsi, trigger, dan RLS.
"""
from __future__ import annotations

import socket
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SEARCH_PATH, AsyncSessionLocal, make_engine
from app.main import app

_DB = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))


def _db_reachable() -> bool:
    try:
        with socket.create_connection((_DB.hostname, _DB.port or 5432), timeout=3):
            return True
    except OSError:
        return False


requires_db = pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL uji tidak dapat dijangkau")


@pytest.fixture(scope="session", autouse=True)
def _null_pool() -> None:
    # Setiap TestClient menjalankan event loop sendiri; koneksi asyncpg tidak boleh dipakai lintas loop.
    AsyncSessionLocal.configure(bind=make_engine(poolclass=NullPool))


def _sync_conn():
    return psycopg2.connect(
        host=_DB.hostname, port=_DB.port, dbname=_DB.path.lstrip("/"),
        user=_DB.username, password=_DB.password,
        options=f"-c search_path={SEARCH_PATH.replace(' ', '')}",
    )


def sync_query(sql: str, params: tuple = ()) -> list[tuple]:
    """Kueri langsung ke DB uji di luar aplikasi (persiapan & pemeriksaan hasil)."""
    with _sync_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if cur.description else []


class SeededUser:
    def __init__(self, org_id: str, user_id: str, login: str, password: str) -> None:
        self.org_id = org_id
        self.user_id = user_id
        self.login = login
        self.password = password

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        return sync_query(sql, params)


@pytest.fixture
def seeded_user() -> Iterator[SeededUser]:
    """Organisasi + pengguna ADMIN sekali pakai; dihapus bersih setelah uji."""
    login = f"uji-{uuid.uuid4().hex[:12]}@contoh.test"
    password = "KataSandiUji-123"
    with _sync_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO vms.organization (name) VALUES ('Organisasi uji') RETURNING id")
        org_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO vms.app_user (organization_id, login, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (org_id, login, hash_password(password)),
        )
        user_id = cur.fetchone()[0]
        cur.execute("INSERT INTO vms.user_role (user_id, role) VALUES (%s, 'ADMIN')", (user_id,))
    try:
        yield SeededUser(str(org_id), str(user_id), login, password)
    finally:
        with _sync_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM vms.login_attempt WHERE login = %s", (login,))
            cur.execute("DELETE FROM vms.organization WHERE id = %s", (org_id,))


@pytest.fixture
def client() -> Iterator[TestClient]:
    # https agar cookie refresh (Secure) disimpan dan dikirim ulang oleh klien uji.
    with TestClient(app, base_url="https://testserver") as c:
        yield c
