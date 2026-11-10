"""Parameter SQL (NIK, rekening, sandi) tidak boleh ikut tercetak di galat/log: engine memakai hide_parameters."""
from __future__ import annotations

from sqlalchemy.exc import StatementError

from app.database.session import engine, make_engine


def test_engine_global_menyembunyikan_parameter():
    assert engine.sync_engine.hide_parameters is True


def test_make_engine_menyembunyikan_parameter_secara_default():
    e = make_engine("postgresql+asyncpg://u:p@localhost:1/x")
    assert e.sync_engine.hide_parameters is True


def test_galat_pernyataan_tidak_memuat_nilai_parameter():
    err = StatementError("gagal", "SELECT :nik", {"nik": "3171234567890001"}, ValueError("x"), hide_parameters=True)
    assert "3171234567890001" not in str(err)
