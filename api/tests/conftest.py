"""
Fixture uji bersama. Uji integrasi memakai PostgreSQL sungguhan (dok 07, dok 12 §1),
bukan SQLite — separuh aturan hidup di fungsi, trigger, dan RLS.
"""
from __future__ import annotations

import contextlib
import os
import socket
import sys
import uuid
from collections.abc import Callable, Iterator
from urllib.parse import urlparse

if sys.platform == "win32":
    _git_bin = r"C:\Program Files\Git\bin"
    if os.path.isdir(_git_bin) and _git_bin.lower() not in os.environ.get("PATH", "").lower():
        os.environ["PATH"] = f"{_git_bin};{os.environ.get('PATH', '')}"

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool

from tests.db_guard import unsafe_test_database, unsafe_test_storage, use_test_database

use_test_database()   # harus sebelum app.* diimpor: pengaturan dibaca saat impor

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import SEARCH_PATH, AsyncSessionLocal, make_engine
from app.main import API_PREFIX, app

_UNSAFE = unsafe_test_database(settings.DATABASE_URL) or unsafe_test_storage(settings.MINIO_ENDPOINT)
if _UNSAFE:
    # A-00 (docs/24): lebih baik suite berhenti daripada menulis data uji ke produksi.
    raise pytest.UsageError(_UNSAFE)

# Persiapan & pemeriksaan data uji (`sync_query`) memakai URL ini; aplikasi tetap memakai DATABASE_URL. Isi dengan
# superuser bila DATABASE_URL memakai peran aplikasi yang tunduk RLS (uji RLS penuh, P9-2).
_SETUP_URL = os.environ.get("TEST_SETUP_DATABASE_URL") or settings.DATABASE_URL
_DB = urlparse(_SETUP_URL.replace("+asyncpg", ""))


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
def _face_enrollment_off() -> None:
    # Uji tidak bergantung pada saklar di api/.env; uji gerbang wajah menyalakannya sendiri (monkeypatch).
    settings.FACE_ENROLLMENT_REQUIRED = False   # sesi penuh: monkeypatch.undo() di uji tidak boleh menghidupkannya lagi


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


# Kantor utama seed Master Schema V2: akun tanpa karyawan memakai kantor ini sebagai "organisasi".
MAIN_OFFICE_ID = "11111111-0000-4000-a000-000000000001"

# Peran V1 lama di uji → system_role V2 (FINANCE & ASSET tidak ada di V2 — keputusan pemilik 2026-10-20).
V2_ROLE = {
    "ADMIN": "SUPER_ADMIN",
    "OPS": "OPERATIONAL_MANAGER",
    "PM": "PROJECT_MANAGER",
    "LEADER": "TEAM_LEADER",
    "HR": "ADMIN_HR_GA",
    None: "EMPLOYEE",
}


@pytest.fixture
def make_user() -> Iterator[Callable[..., SeededUser]]:
    """
    Pabrik akun sekali pakai tanpa karyawan: `make_user("HR")`, `make_user(None)` (karyawan biasa).
    Peran memakai kode lama (ADMIN/HR/PM/OPS/LEADER) atau langsung system_role V2. Dihapus bersih setelah uji.
    """
    from tests.cleanup import purge_login_logs, purge_users

    created: list[str] = []
    logins: list[str] = []

    def _make(role: str | None = "ADMIN") -> SeededUser:
        login = f"uji-{uuid.uuid4().hex[:12]}@contoh.test"
        password = "KataSandiUji-123"
        system_role = V2_ROLE.get(role, role)
        user_id = str(sync_query(
            "INSERT INTO users (username, email, password_hash, system_role) "
            "VALUES (%s, %s, %s, %s::system_role_enum) RETURNING user_id",
            (login.split("@")[0], login, hash_password(password), system_role))[0][0])
        created.append(user_id)
        logins.append(login)
        return SeededUser(MAIN_OFFICE_ID, user_id, login, password)

    try:
        yield _make
    finally:
        conn = _sync_conn()
        try:
            purge_users(conn, created)
            purge_login_logs(conn, logins)
        finally:
            conn.close()


@pytest.fixture
def seeded_user(make_user: Callable[..., SeededUser]) -> SeededUser:
    return make_user("ADMIN")


def login_platform(login: str) -> str:
    """docs/35 §1: peran lapangan (TEAM_LEADER, EMPLOYEE) masuk lewat aplikasi HP, peran kantor lewat web —
    uji login lewat klien yang sesuai, seperti aplikasi sungguhan."""
    rows = sync_query("SELECT system_role::text FROM users WHERE email = %s AND delete_at IS NULL", (login,))
    return "mobile" if rows and rows[0][0] in ("TEAM_LEADER", "EMPLOYEE") else "web"


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


# ── Dunia uji untuk alur per modul (V-02), Master Schema V2 ──────────────────────────────────────
WORLD_PASSWORD = "KataSandiDunia-123"


class World:
    """Satu kantor (office) lengkap: divisi, tim, karyawan, dan akun per peran yang saling tertaut.

    `org_id` = office_id (organisasi di V2), `unit_id` = division_id, `team_id` = tim lapangan
    (ketua = `leader`, anggota = `member`). V2 tidak punya tabel lokasi: `site_id` diisi office_id
    (absen kantor memakai koordinat office)."""

    def __init__(self, tag: str, org_id: str):
        self.tag = tag
        self.org_id = org_id
        self.site_id = org_id
        self.unit_id = ""
        self.team_id = ""
        self.employees: dict[str, str] = {}  # nama peran → employee_id
        self.users: dict[str, str] = {}      # nama peran → user_id
        self.logins: dict[str, str] = {}     # nama peran → email login
        self._headers: dict[str, dict[str, str]] = {}
        self._password_hash = hash_password(WORLD_PASSWORD)

    def add_person(self, who: str, role: str | None, unit_id: str | None = None, **_: object) -> str:
        """Karyawan + akun di kantor ini. `role` = kode lama (ADMIN/HR/PM/OPS/LEADER/None) atau system_role V2."""
        self.employees[who] = str(sync_query(
            "INSERT INTO employee (office_id, division_id, full_name, employee_no, join_date) "
            "VALUES (%s, %s, %s, %s, '2026-01-05') RETURNING employee_id",
            (self.org_id, unit_id or self.unit_id or None, f"Karyawan uji {who}",
             f"UJI-{self.tag}-{len(self.employees):02d}"))[0][0])
        self.logins[who] = f"{who}-{self.tag}@contoh.test"
        self.users[who] = str(sync_query(
            "INSERT INTO users (employee_id, username, email, password_hash, system_role) "
            "VALUES (%s, %s, %s, %s, %s::system_role_enum) RETURNING user_id",
            (self.employees[who], f"{who}-{self.tag}", self.logins[who], self._password_hash,
             V2_ROLE.get(role, role)))[0][0])
        return self.employees[who]

    def add_unit(self, name: str) -> str:
        """Divisi tambahan dengan OM & PM dunia ini."""
        return str(sync_query(
            "INSERT INTO division (om_id, pm_id, name) VALUES (%s, %s, %s) RETURNING division_id",
            (self.employees["ops"], self.employees["pm"], f"Divisi uji {name}"))[0][0])

    def headers(self, client: TestClient, who: str) -> dict[str, str]:
        if who not in self._headers:
            response = client.post("/auth/login", json={"email": self.logins[who], "password": WORLD_PASSWORD,
                                                        "platform": login_platform(self.logins[who])})
            assert response.status_code == 200, response.text
            self._headers[who] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return self._headers[who]


# peran di dunia uji → peran lama (dipetakan ke system_role V2 lewat V2_ROLE)
_WORLD_PEOPLE = {
    "admin": "ADMIN",
    "hr": "HR",
    "pm": "PM",
    "ops": "OPS",
    "leader": "LEADER",
    "member": None,
}


@contextlib.contextmanager
def _build_world() -> Iterator[World]:
    from tests.cleanup import purge_login_logs, purge_office

    tag = uuid.uuid4().hex[:8]
    org_id = str(sync_query(
        "INSERT INTO office (name, address, latitude, longitude) "
        "VALUES (%s, 'Jl. Uji No. 1', -6.2000000, 106.8000000) RETURNING office_id",
        (f"Kantor uji {tag}",))[0][0])
    try:
        built = World(tag, org_id)
        for who, role in _WORLD_PEOPLE.items():
            built.add_person(who, role)
        built.unit_id = built.add_unit("CCTV & ACS")
        sync_query("UPDATE employee SET division_id = %s WHERE office_id = %s", (built.unit_id, org_id))
        built.team_id = str(sync_query(
            "INSERT INTO team (office_id, division_id, leader_employee_id, name) "
            "VALUES (%s, %s, %s, %s) RETURNING team_id",
            (org_id, built.unit_id, built.employees["leader"], f"Tim uji {tag}"))[0][0])
        for who in ("leader", "member"):
            sync_query("INSERT INTO member (team_id, employee_id) VALUES (%s, %s)",
                       (built.team_id, built.employees[who]))
        yield built
    finally:
        conn = _sync_conn()
        try:
            purge_office(conn, org_id)
            purge_login_logs(conn, list(built.logins.values()) if "built" in locals() else [])
        finally:
            conn.close()


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

    import app.core.storage as storage_core

    monkeypatch.setattr(storage_core, "upload_file", upload)
    monkeypatch.setattr(storage_core, "get_presigned_url", lambda name, expires=None: f"https://minio.uji/{name}")

    try:
        import app.modules.system.controllers.files_controller as files_ctrl

        monkeypatch.setattr(files_ctrl, "upload_file", upload)
        monkeypatch.setattr(files_ctrl, "get_presigned_url", lambda name, expires=None: f"https://minio.uji/{name}")
    except (ImportError, AttributeError):
        pass

    return stored

