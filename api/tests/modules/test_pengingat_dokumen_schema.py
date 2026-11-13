"""Skema pengingat dokumen kendaraan (v2_0041): unik/idempoten, CHECK, riwayat aktif tunggal. Hanya definisi."""

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


def _kendaraan(cur) -> tuple[str, str, str]:
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
        "INSERT INTO division (om_id, pm_id, name) VALUES (%s, %s, %s) RETURNING division_id", (emp, emp, f"D{tag[:6]}")
    )
    div = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate) "
        "VALUES (%s, %s, (enum_range(NULL::vehicle_type_enum))[1], 'Mobil', %s) RETURNING vehicle_id",
        (office, div, f"B{tag[:8]}"),
    )
    return str(office), str(cur.fetchone()[0]), str(emp)


def _jenis(cur, code: str = "STNK_UJI") -> str:
    cur.execute(
        "INSERT INTO document_type (code, nama, berlaku_untuk) VALUES (%s, 'STNK', 'KENDARAAN') ON CONFLICT DO NOTHING",
        (code,),
    )
    return code


def test_default_ambang_dan_check_jenis(conn) -> None:
    cur = conn.cursor()
    code = f"T{uuid.uuid4().hex[:8]}"
    _jenis(cur, code)
    cur.execute("SELECT ambang_hari, harian_mulai_hari FROM document_type WHERE code = %s", (code,))
    assert cur.fetchone() == ([30, 21, 14], 7)
    _fail(
        cur,
        "INSERT INTO document_type (code, nama, berlaku_untuk) VALUES ('X1', 'x', 'LAIN')",
        (),
        psycopg2.errors.CheckViolation,
    )


def test_dokumen_aktif_tunggal_dan_riwayat(conn) -> None:
    cur = conn.cursor()
    office, veh, _emp = _kendaraan(cur)
    code = _jenis(cur, f"T{uuid.uuid4().hex[:8]}")
    ins = (
        "INSERT INTO vehicle_document (office_id, vehicle_id, doc_type_code, expired_on, status) "
        "VALUES (%s, %s, %s, '2027-01-01', %s)"
    )
    cur.execute(ins, (office, veh, code, "active"))
    _fail(cur, ins, (office, veh, code, "active"), psycopg2.errors.UniqueViolation)
    cur.execute(ins, (office, veh, code, "replaced"))
    cur.execute(ins, (office, veh, code, "replaced"))
    _fail(cur, ins, (office, veh, code, "kadaluarsa"), psycopg2.errors.CheckViolation)
    _fail(
        cur,
        "INSERT INTO vehicle_document (office_id, vehicle_id, doc_type_code, issued_on, expired_on) "
        "VALUES (%s, %s, %s, '2028-01-01', '2027-01-01')",
        (office, veh, code),
        psycopg2.errors.CheckViolation,
    )


def test_log_pengingat_idempoten(conn) -> None:
    cur = conn.cursor()
    office, _, _ = _kendaraan(cur)
    doc = str(uuid.uuid4())
    ins = (
        "INSERT INTO document_reminder (office_id, doc_kind, doc_id, due_date, stage, send_date) "
        "VALUES (%s, 'VEHICLE_DOCUMENT', %s, '2027-01-01', %s, %s) ON CONFLICT DO NOTHING"
    )
    cur.execute(ins, (office, doc, "DAILY", "2026-12-25"))
    cur.execute(ins, (office, doc, "DAILY", "2026-12-25"))
    cur.execute(ins, (office, doc, "DAILY", "2026-12-26"))
    cur.execute(ins, (office, doc, "T30", "2026-12-02"))
    cur.execute(ins, (office, doc, "T30", "2026-12-03"))  # tahap sekali: hari lain tidak ganda
    cur.execute("SELECT stage, count(*) FROM document_reminder WHERE doc_id = %s GROUP BY stage", (doc,))
    assert dict(cur.fetchall()) == {"DAILY": 2, "T30": 1}
    _fail(
        cur,
        ins.replace(" ON CONFLICT DO NOTHING", ""),
        (office, doc, "T99", "2026-12-02"),
        psycopg2.errors.CheckViolation,
    )


def test_pengemudi_aktif_tunggal(conn) -> None:
    cur = conn.cursor()
    office, veh, emp = _kendaraan(cur)
    ins = "INSERT INTO vehicle_driver (office_id, vehicle_id, employee_id, selesai_on) VALUES (%s, %s, %s, %s)"
    cur.execute(ins, (office, veh, emp, None))
    _fail(cur, ins, (office, veh, emp, None), psycopg2.errors.UniqueViolation)
    _fail(cur, ins, (office, veh, emp, "2000-01-01"), psycopg2.errors.CheckViolation)
