"""
V-01 · Setiap literal SQL di aplikasi cocok dengan skema sungguhan (tabel, kolom, enum, fungsi,
tipe). Kueri di-PREPARE tanpa dieksekusi. Mencegah terulangnya publish SK → 500 karena kolom
`valid_to` yang tidak ada (PLAN-VERIFIKASI-MODUL E1/E2).

`KNOWN_BROKEN` hanya boleh MENYUSUT: uji gagal bila ada kueri rusak baru, dan juga bila kueri di
daftar ini ternyata sudah benar (hapus barisnya).
"""
from __future__ import annotations

import psycopg2
import pytest

from tests.conftest import _sync_conn, requires_db
from tests.sql_inventory import collect

pytestmark = requires_db

# kunci → task yang memperbaikinya (PLAN-VERIFIKASI-MODUL-RINCI.md)
KNOWN_BROKEN: dict[str, str] = {}  # kosong sejak V-14 — kueri baru yang tak cocok skema langsung merah


def _prepare_errors() -> dict[str, str]:
    literals, _ = collect()
    errors: dict[str, str] = {}
    conn = _sync_conn()
    conn.autocommit = True
    try:
        cur = conn.cursor()
        for lit in literals:
            try:
                cur.execute(f"PREPARE _cek AS {lit.as_prepared()}")
                cur.execute("DEALLOCATE _cek")
            except psycopg2.Error as e:
                errors[lit.key] = f"{lit.path}:{lit.line}: {str(e).splitlines()[0]}"
                cur.execute("DEALLOCATE ALL")  # jangan biarkan _cek tersisa → kegagalan palsu berantai
    finally:
        conn.close()
    return errors


@pytest.fixture(scope="module")
def errors() -> dict[str, str]:
    return _prepare_errors()


def test_inventory_is_not_empty():
    literals, _ = collect()
    assert len(literals) > 100


def test_no_new_query_mismatches_schema(errors):
    new = {k: v for k, v in errors.items() if k not in KNOWN_BROKEN}
    assert not new, "Kueri tidak cocok skema:\n" + "\n".join(f"  {k}  {v}" for k, v in sorted(new.items()))


def test_known_broken_list_only_shrinks(errors):
    fixed = sorted(k for k in KNOWN_BROKEN if k not in errors)
    assert not fixed, f"Sudah benar — hapus dari KNOWN_BROKEN: {fixed}"
