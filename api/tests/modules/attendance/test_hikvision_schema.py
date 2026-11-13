"""Skema absensi Hikvision (v2_0040): kunci idempotensi, CHECK, kolom sumber. Hanya definisi, tanpa logika API."""
import uuid

import psycopg2
import pytest

from tests.conftest import _sync_conn, requires_db

pytestmark = requires_db


@pytest.fixture()
def conn():
    c = _sync_conn()
    c.autocommit = False
    try:
        yield c
    finally:
        c.rollback()
        c.close()


def _device(cur, mode: str = "SHADOW") -> str:
    tag = uuid.uuid4().hex
    cur.execute(
        "INSERT INTO office (name, address, latitude, longitude) "
        "VALUES (%s, 'Jl. Uji', -6.2, 106.8) RETURNING office_id",
        (f"Kantor {tag[:8]}",),
    )
    office_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO hikvision_device (office_id, name, ip_address, serial_no, token_hash, mode) "
        "VALUES (%s, 'Pintu', '192.168.1.10', %s, %s, %s) RETURNING device_id",
        (office_id, f"SN{tag[:12]}", tag + tag[:32], mode),
    )
    return str(cur.fetchone()[0])


def _event(cur, device_id: str, serial: int | None, key: str | None = None, sumber: str = "PUSH") -> None:
    cur.execute(
        "INSERT INTO hikvision_event (device_id, serial_no_event, event_key, major_event_type, minor_event_type, "
        "event_time, payload, sumber) VALUES (%s, %s, %s, 5, 75, now(), '{}'::jsonb, %s)",
        (device_id, serial, key, sumber),
    )


def test_event_serial_unik_per_perangkat(conn) -> None:
    cur = conn.cursor()
    dev = _device(cur)
    _event(cur, dev, 100)
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _event(cur, dev, 100, sumber="PULL")
    cur.execute("ROLLBACK TO SAVEPOINT s")
    _event(cur, dev, 101)


def test_event_kunci_cadangan_dan_check(conn) -> None:
    cur = conn.cursor()
    dev = _device(cur)
    key = "a" * 64
    _event(cur, dev, None, key)
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _event(cur, dev, None, key)
    cur.execute("ROLLBACK TO SAVEPOINT s")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _event(cur, dev, None, None)
    cur.execute("ROLLBACK TO SAVEPOINT s")


def test_check_sumber_dan_mode(conn) -> None:
    cur = conn.cursor()
    dev = _device(cur)
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _event(cur, dev, 1, sumber="LAIN")
    cur.execute("ROLLBACK TO SAVEPOINT s")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _device(cur, mode="LAIN")


def test_attendance_kolom_sumber_nullable(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT column_name, is_nullable FROM information_schema.columns "
        "WHERE table_name = 'attendance' AND column_name IN ('source', 'device_event_id')"
    )
    assert dict(cur.fetchall()) == {"source": "YES", "device_event_id": "YES"}
    cur.execute("SELECT convalidated FROM pg_constraint WHERE conname = 'ck_attendance_source'")
    assert cur.fetchone() == (True,)
