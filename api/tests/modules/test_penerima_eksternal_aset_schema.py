"""Skema penerima eksternal aset (v2_0043, ADR 0003): CHECK satu penerima, FK, indeks. Hanya definisi."""

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


def _fail(cur, sql: str, params, exc) -> None:
    cur.execute("SAVEPOINT s")
    with pytest.raises(exc):
        cur.execute(sql, params)
    cur.execute("ROLLBACK TO SAVEPOINT s")


def _dasar(cur) -> tuple[str, str, str]:
    tag = uuid.uuid4().hex
    cur.execute(
        "INSERT INTO office (name, address, latitude, longitude) VALUES (%s, 'Jl. Uji', -6.2, 106.8) "
        "RETURNING office_id",
        (f"Kantor {tag[:8]}",),
    )
    office = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO employee (office_id, full_name, employee_no, join_date) VALUES (%s, 'Uji', %s, now()) "
        "RETURNING employee_id",
        (office, f"E{tag[:10]}"),
    )
    emp = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO tool (office_id, ownership_type, category, name, tool_code) "
        "VALUES (%s, 'SHARED_TOOL', 'LAINNYA', 'Alat', %s) RETURNING tool_id",
        (office, f"T{tag[:10]}"),
    )
    return str(office), str(emp), str(cur.fetchone()[0])


def _penerima(cur, office: str) -> str:
    cur.execute(
        "INSERT INTO asset_external_borrowers (office_id, nama, instansi, kontak) "
        "VALUES (%s, 'PT Klien', 'Pertamina', '0812') RETURNING borrower_id",
        (office,),
    )
    return str(cur.fetchone()[0])


_INS = (
    "INSERT INTO asset_assignment (asset_type, tool_id, employee_id, external_borrower_id, due_date) "
    "VALUES ('TOOL', %s, %s, %s, '2026-12-31')"
)


def test_tepat_satu_penerima(conn) -> None:
    cur = conn.cursor()
    office, emp, tool = _dasar(cur)
    b = _penerima(cur, office)
    _fail(cur, _INS, (tool, None, None), psycopg2.errors.CheckViolation)
    _fail(cur, _INS, (tool, emp, b), psycopg2.errors.CheckViolation)
    cur.execute(_INS, (tool, None, b))  # eksternal saja
    cur.execute(_INS, (tool, emp, None))  # karyawan saja (perilaku lama)


def test_fk_dan_nama_wajib(conn) -> None:
    cur = conn.cursor()
    office, _emp, tool = _dasar(cur)
    _fail(cur, _INS, (tool, None, str(uuid.uuid4())), psycopg2.errors.ForeignKeyViolation)
    _fail(
        cur,
        "INSERT INTO asset_external_borrowers (office_id, nama) VALUES (%s, '  ')",
        (office,),
        psycopg2.errors.CheckViolation,
    )


def test_indeks_ada(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT count(*) FROM pg_indexes WHERE indexname IN ("
        "'ix_asset_ext_borrower_office_nama','ix_asset_assignment_ext_borrower',"
        "'ix_asset_assignment_handover_file','ix_asset_assignment_due_open')"
    )
    assert cur.fetchone()[0] == 4
