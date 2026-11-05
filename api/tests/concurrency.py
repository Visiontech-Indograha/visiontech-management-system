"""Pembantu tes konkurensi: dua permintaan serentak (Barrier) dan transaksi tertahan di koneksi kedua.

`tahan_lalu_ubah` memegang baris lewat koneksi lain (belum commit), menjalankan permintaan, menunggu sampai
permintaan itu masuk antrean kunci baris, lalu commit. Permintaan yang benar membaca status terkini (409),
bukan menimpanya. Tes ini deterministik; `dua_bersamaan` menguji dua permintaan yang benar-benar serentak.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from tests.conftest import _sync_conn, sync_query


def tunggu_terkunci(penahan_pid: int, batas: int = 200) -> None:
    """Tunggu sampai ada sesi yang diblokir OLEH koneksi penahan (`penahan_pid`), yaitu permintaan tes ini
    sudah masuk antrean kunci. Disaring per pid: tes konkurensi lain (worker xdist lain di DB yang sama)
    tidak ikut terhitung."""
    for _ in range(batas):
        if sync_query("SELECT count(*) FROM pg_stat_activity "
                      "WHERE wait_event_type = 'Lock' AND datname = current_database() "
                      "AND %s = ANY(pg_blocking_pids(pid))", (penahan_pid,))[0][0] > 0:
            return
        time.sleep(0.05)
    pytest.fail("Permintaan tidak menunggu kunci baris; kunci (FOR UPDATE / UPDATE bersyarat) belum berjalan")


def dua_bersamaan(aksi: Callable[[int], Any]) -> list[Any]:
    """Dua permintaan dimulai bersamaan setelah Barrier. `aksi(i)` mengembalikan respons HTTP."""
    barrier = threading.Barrier(2)

    def kirim(i: int) -> Any:
        barrier.wait()
        return aksi(i)

    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(kirim, range(2)))


def tahan_lalu_ubah(sql: str, params: tuple, aksi: Callable[[], Any]) -> Any:
    """Koneksi kedua menjalankan `sql` lalu menahan baris (belum commit); `aksi` harus menunggu lalu
    menjawab sesuai status setelah commit."""
    conn = _sync_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_backend_pid()")
            penahan_pid = cur.fetchone()[0]
            cur.execute(sql, params)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(aksi)
            tunggu_terkunci(penahan_pid)
            conn.commit()
            return future.result(timeout=30)
    finally:
        conn.close()
