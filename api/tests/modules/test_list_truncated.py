"""Daftar tanpa paginasi yang terpotong di MAX_ROWS_UNPAGED diberi header X-Result-Truncated."""
from fastapi import Response

from app.core.list_params import MAX_ROWS_UNPAGED, TRUNCATED_HEADER, ListParams, apply_list


def _run(n: int, **kw: int) -> Response:
    resp = Response()
    apply_list(range(n), ListParams(q=None, page=kw.get("page"), size=kw.get("size")), resp, lambda r: [r])
    return resp


def test_terpotong_diberi_penanda() -> None:
    assert _run(MAX_ROWS_UNPAGED).headers[TRUNCATED_HEADER] == "true"


def test_di_bawah_batas_tanpa_penanda() -> None:
    assert TRUNCATED_HEADER not in _run(MAX_ROWS_UNPAGED - 1).headers


def test_paginasi_tanpa_penanda() -> None:
    assert TRUNCATED_HEADER not in _run(MAX_ROWS_UNPAGED, page=1).headers
