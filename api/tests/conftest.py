"""
Fixture uji bersama. Uji integrasi memakai PostgreSQL sungguhan (dok 07, dok 12 §1),
bukan SQLite — separuh aturan hidup di fungsi, trigger, dan RLS.
"""
from __future__ import annotations

import contextlib
import os
import socket
import uuid
from collections.abc import Callable, Iterator
from urllib.parse import urlparse

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool

from tests.db_guard import unsafe_test_database, unsafe_test_storage, use_test_database

use_test_database()   # harus sebelum app.* diimpor: pengaturan dibaca saat impor

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SEARCH_PATH, AsyncSessionLocal, make_engine
from app.main import API_PREFIX, app

_UNSAFE = unsafe_test_database(settings.DATABASE_URL) or unsafe_test_storage(settings.MINIO_ENDPOINT)
if _UNSAFE:
    # A-00 (docs/24): lebih baik suite berhenti daripada menulis data uji ke produksi.
    raise pytest.UsageError(_UNSAFE)

_DB = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))


def _db_reachable() -> bool:
    try:
        with socket.create_connection((_DB.hostname, _DB.port or 5432), timeout=3):
            return True
    except OSError:
        return False


_DB_OK = _db_reachable()
if not _DB_OK and os.getenv("VMS_REQUIRE_DB"):
    # Di CI uji DB tidak boleh diam-diam dilewati — itu sama dengan tidak diuji sama sekali.
    raise RuntimeError(f"VMS_REQUIRE_DB diset tetapi PostgreSQL {_DB.hostname}:{_DB.port} tidak dapat dijangkau")

requires_db = pytest.mark.skipif(not _DB_OK, reason="PostgreSQL uji tidak dapat dijangkau")


@pytest.fixture(scope="session", autouse=True)
def _null_pool() -> None:
    # Setiap TestClient menjalankan event loop sendiri; koneksi asyncpg tidak boleh dipakai lintas loop.
    AsyncSessionLocal.configure(bind=make_engine(poolclass=NullPool))


def _sync_conn():
    return psycopg2.connect(
        host=_DB.hostname, port=_DB.port, dbname=_DB.path.lstrip("/"),
        user=_DB.username, password=_DB.password,
        options=f"-c search_path={SEARCH_PATH.replace(' ', '')}",
        # DB uji ada di server (Tailscale): jaringan putus → gagal cepat, bukan menggantung berjam-jam.
        connect_timeout=15, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3,
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
def make_user() -> Iterator[Callable[..., SeededUser]]:
    """
    Pabrik pengguna sekali pakai: `make_user("HR")`, `make_user(None)` (tanpa peran global).
    Setiap pengguna mendapat organisasi sendiri; semuanya dihapus bersih setelah uji.
    """
    created: list[tuple[str, str]] = []

    def _make(role: str | None = "ADMIN") -> SeededUser:
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
            if role:
                cur.execute("INSERT INTO vms.user_role (user_id, role) VALUES (%s, %s)", (user_id, role))
        created.append((str(org_id), login))
        return SeededUser(str(org_id), str(user_id), login, password)

    try:
        yield _make
    finally:
        with _sync_conn() as conn, conn.cursor() as cur:
            for org_id, login in created:
                cur.execute("DELETE FROM vms.login_attempt WHERE login = %s", (login,))
                cur.execute("DELETE FROM vms.organization WHERE id = %s", (org_id,))


@pytest.fixture
def seeded_user(make_user: Callable[..., SeededUser]) -> SeededUser:
    """Pengguna ADMIN sekali pakai."""
    return make_user("ADMIN")


def login_platform(login: str) -> str:
    """R-33: aplikasi HP hanya untuk staf lapangan, web hanya untuk akun kantor — uji login lewat
    klien yang sesuai jenis pekerja akun (seperti aplikasi sungguhan)."""
    rows = sync_query("SELECT e.attendance_mode FROM vms.app_user u LEFT JOIN vms.employee e ON e.id = u.employee_id "
                      "WHERE u.login = %s", (login,))
    return "mobile" if rows and rows[0][0] == "FIELD" else "web"


def login_headers(client: TestClient, user: SeededUser) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": user.login, "password": user.password,
                                                "platform": login_platform(user.login)})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    # https agar cookie refresh (Secure) disimpan dan dikirim ulang; jalur relatif terhadap /api/v1.
    with TestClient(app, base_url=f"https://testserver{API_PREFIX}") as c:
        yield c


# ── Dunia uji untuk alur per modul (V-02) ─────────────────────────────────────────────────────
WORLD_PASSWORD = "KataSandiDunia-123"


class World:
    """Satu organisasi lengkap: unit, lokasi, karyawan, dan pengguna per peran yang saling tertaut."""

    def __init__(self, tag: str, org_id: str, unit_id: str, site_id: str):
        self.tag = tag
        self.org_id = org_id
        self.unit_id = unit_id
        self.site_id = site_id
        self.employees: dict[str, str] = {}  # nama peran → employee_id
        self.logins: dict[str, str] = {}     # nama peran → login
        self._headers: dict[str, dict[str, str]] = {}
        self._password_hash = hash_password(WORLD_PASSWORD)

    def add_unit(self, code: str) -> str:
        return str(sync_query(
            "INSERT INTO vms.business_unit (organization_id, code, name) VALUES (%s, %s, %s) RETURNING id",
            (self.org_id, code, f"Unit uji {code}"))[0][0])

    def add_person(self, who: str, role: str | None, unit_id: str | None = None, *, per_unit: bool = False) -> str:
        """Karyawan + akun (+ peran global) di organisasi ini. → employee_id."""
        unit = unit_id or self.unit_id
        self.employees[who] = str(sync_query(
            "INSERT INTO vms.employee (organization_id, employee_no, full_name, position, unit_id, join_date) "
            "VALUES (%s, %s, %s, 'Teknisi', %s, '2026-01-05') RETURNING id",
            (self.org_id, f"UJI-{len(self.employees):02d}", f"Karyawan uji {who}", unit))[0][0])
        self.logins[who] = f"{who}-{self.tag}@contoh.test"
        user_id = sync_query(
            "INSERT INTO vms.app_user (organization_id, login, password_hash, employee_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (self.org_id, self.logins[who], self._password_hash, self.employees[who]))[0][0]
        if role:
            sync_query("INSERT INTO vms.user_role (user_id, role, unit_id) VALUES (%s, %s, %s)",
                       (user_id, role, unit if per_unit else None))
        return self.employees[who]

    def headers(self, client: TestClient, who: str) -> dict[str, str]:
        if who not in self._headers:
            response = client.post("/auth/login", json={"email": self.logins[who], "password": WORLD_PASSWORD,
                                                        "platform": login_platform(self.logins[who])})
            assert response.status_code == 200, response.text
            self._headers[who] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return self._headers[who]


# peran di dunia uji → (peran global, apakah per unit)
_WORLD_PEOPLE = {
    "admin": ("ADMIN", False),
    "hr": ("HR", False),
    "pm": ("PM", True),
    "finance": ("FINANCE", False),
    "asset": ("ASSET", False),
    "ops": ("OPS", False),
    "leader": (None, False),   # ketua & anggota berasal dari SK, bukan peran global
    "member": (None, False),
}


@contextlib.contextmanager
def _build_world() -> Iterator[World]:
    from tests.cleanup import purge_organization

    tag = uuid.uuid4().hex[:8]
    org_id = str(sync_query("INSERT INTO vms.organization (name) VALUES (%s) RETURNING id", (f"Dunia uji {tag}",))[0][0])
    try:
        unit_id = str(sync_query(
            "INSERT INTO vms.business_unit (organization_id, code, name) VALUES (%s, 'CCTV_ACS', 'CCTV & ACS') RETURNING id",
            (org_id,))[0][0])
        site_id = str(sync_query(
            # R-33: lokasi proyek milik unit uji — pekerja lapangan hanya absen di lokasi unitnya.
            "INSERT INTO vms.site (organization_id, name, location, radius_m, unit_id) "
            "VALUES (%s, 'Gudang uji', ST_GeogFromText('POINT(106.8 -6.2)'), 100, %s) RETURNING id",
            (org_id, unit_id))[0][0])
        built = World(tag, org_id, unit_id, site_id)
        for who, (role, per_unit) in _WORLD_PEOPLE.items():
            built.add_person(who, role, per_unit=per_unit)
        yield built
    finally:
        conn = _sync_conn()
        try:
            purge_organization(conn, org_id)
        finally:
            conn.close()
        sync_query("DELETE FROM vms.login_attempt WHERE login LIKE %s", (f"%-{tag}@contoh.test",))


@pytest.fixture
def world() -> Iterator[World]:
    with _build_world() as built:
        yield built


@pytest.fixture
def other_world() -> Iterator[World]:
    """Organisasi kedua — untuk memastikan data lintas organisasi tidak terlihat (404)."""
    with _build_world() as built:
        yield built


@pytest.fixture
def fake_storage(monkeypatch) -> dict[str, bytes]:
    """Penyimpanan berkas di memori — uji alur memeriksa DB; MinIO diuji di test_storage.py."""
    stored: dict[str, bytes] = {}

    def upload(object_name: str, data: bytes, content_type: str) -> bool:
        stored[object_name] = data
        return True

    import app.api.v1.endpoints.files as files_api

    monkeypatch.setattr(files_api, "upload_file", upload)
    monkeypatch.setattr(files_api, "get_presigned_url", lambda name, expires=None: f"https://minio.uji/{name}")
    return stored
