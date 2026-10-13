"""Insiden 2026-10-13: sandi DB berkarkter ``@`` di ``api.env`` produksi ditulis mentah sehingga
SQLAlchemy membaca ``@`` pertama sebagai pemisah userinfo/host. Host menjadi
``ss@vms_db_prod`` dan API mati dengan ``socket.gaierror`` yang menyesatkan (terlihat seperti
masalah DNS, padahal salah parse URL). ``/ready`` menjawab 503 dan migrasi alembic putus.

Uji ini mengunci perilaku: sandi berkarkter khusus WAJIB di-encode, dan URL yang sudah benar
tidak boleh diubah sama sekali.
"""
from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings, encode_url_credentials, normalize_database_url_port

_HOST = "vms_db_prod"


def _url(password: str) -> str:
    return f"postgresql+asyncpg://vms_api:{password}@{_HOST}:5432/visiontech_db"


def _settings(url: str, **over: str) -> Settings:
    return Settings(_env_file=None, DATABASE_URL=url, **over)  # type: ignore[arg-type]


# ── encode_url_credentials ────────────────────────────────────────────────────────────────────

def test_plain_url_is_left_untouched():
    url = "postgresql+asyncpg://vms_app:rahasia@localhost:5433/visiontech_db"
    assert encode_url_credentials(url) == (url, False)


def test_at_sign_in_password_is_encoded():
    url = f"postgresql+asyncpg://vms_api:P@sswordContoh123@{_HOST}:5432/visiontech_db"
    fixed, changed = encode_url_credentials(url)
    assert changed is True
    assert "P%40sswordContoh123" in fixed
    parsed = make_url(fixed)
    assert parsed.host == _HOST                      # inilah yang dulu menjadi 'ss@vms_db_prod'
    assert parsed.password == "P@sswordContoh123"
    assert parsed.username == "vms_api"


@pytest.mark.parametrize("password", [
    "P@ss",                   # '@' tunggal
    "P@sswordContoh123",      # '@' di tengah sandi
    "a@b@c",                  # beberapa '@'
    "P@ss#y",                 # '@' + '#'
])
def test_passwords_with_at_sign_are_repaired(password: str):
    url = f"postgresql+asyncpg://vms_api:{password}@{_HOST}:5432/visiontech_db"
    fixed, changed = encode_url_credentials(url)
    assert changed is True
    parsed = make_url(fixed)
    assert parsed.password == password
    assert parsed.host == _HOST
    assert parsed.database == "visiontech_db"


@pytest.mark.parametrize("password", ["pa:ss", "pa/ss", "pa?ss", "pa#ss", "pa ss", "pa%ss"])
def test_passwords_sqlalchemy_already_parses_correctly_are_not_touched(password: str):
    """Terbukti ter-parse benar (host tetap bersih) — menulis ulang justru berisiko."""
    url = f"postgresql+asyncpg://vms_api:{password}@{_HOST}:5432/visiontech_db"
    assert make_url(url).host == _HOST               # prasyarat: memang sudah benar
    assert encode_url_credentials(url) == (url, False)


@pytest.mark.parametrize("password", ["p@ss/word", "p@ss?x"])
def test_known_blind_spot_is_documented_not_guessed(password: str):
    """Batas yang diketahui: '@' bersama '/' atau '?' menghasilkan URL yang tampak sehat.

    Memperlebar deteksi akan berisiko merusak query string yang sah (``/db?sslmode=require``),
    jadi kasus ini sengaja dibiarkan dan ditangkap oleh pemeriksaan koneksi sungguhan
    (``wait_api_reaches_db`` + ``db_hint`` di ``deploy/autodeploy.sh``). Uji ini mengunci
    kenyataan itu supaya batasnya terlihat, bukan tersembunyi.
    """
    url = f"postgresql+asyncpg://vms_api:{password}@{_HOST}:5432/visiontech_db"
    _, changed = encode_url_credentials(url)
    assert changed is False
    assert make_url(url).host != _HOST               # memang salah bentuk, tapi tidak terdeteksi di sini


def test_at_sign_in_database_name_alone_does_not_trigger_a_rewrite():
    """Nama basis data yang memuat '@' sah; host tetap bersih sehingga tidak boleh diubah."""
    url = "postgresql+asyncpg://vms_app:rahasia@localhost:5433/db@nama"
    assert encode_url_credentials(url) == (url, False)


def test_unparseable_url_is_returned_unchanged():
    for broken in ("bukan-url", "postgresql+asyncpg://", ""):
        assert encode_url_credentials(broken) == (broken, False)


def test_already_encoded_url_is_not_double_encoded():
    url = f"postgresql+asyncpg://vms_api:P%40ss@{_HOST}:5432/visiontech_db"
    assert encode_url_credentials(url) == (url, False)


# ── Settings: perbaikan otomatis ──────────────────────────────────────────────────────────────

def test_settings_repairs_raw_at_sign_in_database_url():
    settings = _settings(_url("P@ss"))
    parsed = make_url(settings.DATABASE_URL)
    assert parsed.host == _HOST
    assert parsed.password == "P@ss"


def test_settings_repairs_migration_url_too():
    settings = _settings(
        f"postgresql+asyncpg://vms_api:aman@{_HOST}:5432/visiontech_db",
        MIGRATION_DATABASE_URL=_url("P@ss"),
    )
    parsed = make_url(settings.MIGRATION_DATABASE_URL)
    assert parsed.host == _HOST
    assert parsed.password == "P@ss"


def test_settings_keeps_well_formed_url_byte_for_byte():
    url = f"postgresql+asyncpg://vms_app:rahasia@{_HOST}:5432/visiontech_db"
    assert url == _settings(url).DATABASE_URL


def test_settings_tolerates_empty_migration_url():
    assert _settings(_url("aman")).MIGRATION_DATABASE_URL == ""


def test_repair_is_logged_so_it_is_not_silent(caplog):
    with caplog.at_level("WARNING"):
        _settings(_url("P@ss"))
    assert "DATABASE_URL" in caplog.text
    assert "belum di-URL-encode" in caplog.text


# ── normalize_database_url_port ───────────────────────────────────────────────────────────────

def test_normalize_container_port_5433_to_5432():
    url = f"postgresql+asyncpg://vms_api:rahasia@{_HOST}:5433/visiontech_db"
    fixed, changed = normalize_database_url_port(url)
    assert changed is True
    parsed = make_url(fixed)
    assert parsed.host == _HOST
    assert parsed.port == 5432
    assert parsed.username == "vms_api"
    assert parsed.password == "rahasia"


def test_localhost_port_5433_is_not_modified():
    url = "postgresql+asyncpg://vms_app:rahasia@localhost:5433/visiontech_db"
    fixed, changed = normalize_database_url_port(url)
    assert changed is False
    assert fixed == url


def test_container_port_already_5432_is_not_modified():
    url = f"postgresql+asyncpg://vms_api:rahasia@{_HOST}:5432/visiontech_db"
    fixed, changed = normalize_database_url_port(url)
    assert changed is False
    assert fixed == url


def test_settings_auto_normalizes_container_port_5433(caplog):
    url = f"postgresql+asyncpg://vms_api:rahasia@{_HOST}:5433/visiontech_db"
    with caplog.at_level("WARNING"):
        settings = _settings(url)
    parsed = make_url(settings.DATABASE_URL)
    assert parsed.host == _HOST
    assert parsed.port == 5432
    assert "port host 5433" in caplog.text
    assert "diperbaiki otomatis ke 5432" in caplog.text
