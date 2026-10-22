"""
T-06 · Bentuk galat baku (dok 05 §2): `{"error": {"code", "message", "details"}}`, message Bahasa
Indonesia untuk manusia, kode sesuai status, dan tidak ada isi galat internal yang bocor.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import register_error_handlers
from app.main import app as real_app

RAW_DB_ERROR = 'duplicate key value violates unique constraint "site_org_name_key" DETAIL: Key (name)=(Gudang)'


class Payload(BaseModel):
    qty: int


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/http/{status_code}")
    async def http(status_code: int) -> None:
        raise HTTPException(status_code=status_code)

    @app.get("/custom-conflict")
    async def custom_conflict() -> None:
        raise HTTPException(status_code=409, detail="Aset sudah dialokasikan ke pekerjaan lain.")

    @app.get("/db-error")
    async def db_error() -> None:
        raise HTTPException(status_code=400, detail={"code": "DB_ERROR", "message": RAW_DB_ERROR})

    @app.get("/http-500")
    async def http_500() -> None:
        raise HTTPException(status_code=500, detail="Internal server error: connection refused 10.0.0.5")

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("rahasia internal")

    @app.post("/validate")
    async def validate(payload: Payload) -> Payload:
        return payload

    return TestClient(app, raise_server_exceptions=False)


def _error(response) -> dict:
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    return body["error"]


@pytest.mark.parametrize(
    ("status_code", "code"),
    [
        (400, "BAD_REQUEST"),
        (401, "UNAUTHENTICATED"),
        (403, "FORBIDDEN"),
        (404, "NOT_FOUND"),
        (405, "METHOD_NOT_ALLOWED"),
        (409, "CONFLICT"),
        (413, "PAYLOAD_TOO_LARGE"),
        (429, "TOO_MANY_REQUESTS"),
        (500, "INTERNAL_ERROR"),
        (503, "INTERNAL_ERROR"),
    ],
)
def test_status_maps_to_code_with_indonesian_message(status_code: int, code: str):
    response = _client().get(f"/http/{status_code}")
    error = _error(response)

    assert response.status_code == status_code
    assert error["code"] == code
    # Frasa standar HTTP berbahasa Inggris tidak boleh sampai ke pengguna.
    for english in ("Not Found", "Forbidden", "Unauthorized", "Bad Request", "Internal Server Error",
                    "Method Not Allowed", "Conflict", "Too Many Requests"):
        assert english not in error["message"]


def test_application_message_is_kept():
    error = _error(_client().get("/custom-conflict"))

    assert error == {"code": "CONFLICT", "message": "Aset sudah dialokasikan ke pekerjaan lain.", "details": {}}


def test_raw_database_error_never_reaches_client():
    response = _client().get("/db-error")
    error = _error(response)

    assert response.status_code == 400
    assert error["code"] == "DB_ERROR"
    assert "constraint" not in response.text and "Gudang" not in response.text


def test_5xx_detail_is_replaced_by_generic_message():
    response = _client().get("/http-500")

    assert _error(response)["code"] == "INTERNAL_ERROR"
    assert "10.0.0.5" not in response.text


def test_unhandled_exception_is_generic_500():
    response = _client().get("/crash")

    assert response.status_code == 500
    assert _error(response)["code"] == "INTERNAL_ERROR"
    assert "rahasia" not in response.text


def test_validation_error_lists_fields():
    response = _client().post("/validate", json={"qty": "banyak"})
    error = _error(response)

    assert response.status_code == 422
    assert error["code"] == "VALIDATION_ERROR"
    assert "qty" in error["details"]["fields"]


def test_no_english_error_messages_in_source():
    """Penjaga regresi K-19: pesan galat di kode aplikasi selalu Bahasa Indonesia."""
    import re
    from pathlib import Path

    english = re.compile(r"(not found|not enough|could not|invalid token|forbidden|unauthorized|"
                         r"internal server error|something went wrong)", re.IGNORECASE)
    message_literal = re.compile(r"""(?:detail|message)\s*=\s*f?["']([^"']+)["']""")
    offenders = [
        f"{path.as_posix()}: {text}"
        for path in Path("app").rglob("*.py")
        for text in message_literal.findall(path.read_text(encoding="utf-8"))
        if english.search(text)
    ]

    assert offenders == []



_ERROR_CALLS = {"AppError": 1, "NotFoundError": 0, "ConflictError": 0, "ValidationError": 0, "ForbiddenError": 0,
                "_reject": 1, "_state": 0, "_invalid": 0}
# P9-4: istilah teknis / Inggris yang tidak dipahami orang lapangan. Pakai "SK", "draf", "diperiksa", "masa kerja".
_JARGON = (r"\b(work plan|draft|offboard\w*|review\w*|checklist|token|server|keystore|payload|endpoint|uuid|"
           r"embedding|internal|request|database)\b")


def _user_facing_messages() -> list[tuple[str, str]]:
    """Teks pesan galat yang sampai ke pengguna: argumen pesan konstruktor galat, termasuk konstanta modul."""
    import ast
    from pathlib import Path

    def text(node: ast.AST | None, consts: dict[str, str]) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
        if isinstance(node, ast.Name):
            return consts.get(node.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            return text(node.func.value, consts)
        return None

    found = []
    for path in Path("app").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        consts = {t.id: v for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, ast.Name) and (v := text(n.value, {}))}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in _ERROR_CALLS:
                continue
            i = _ERROR_CALLS[name]
            arg = node.args[i] if len(node.args) > i else next(
                (k.value for k in node.keywords if k.arg == "message"), None)
            if (msg := text(arg, consts)):
                found.append((f"{path.as_posix()}:{node.lineno}", msg))
    return found


def test_error_messages_avoid_technical_jargon():
    """P9-4 · pesan galat harus bisa dipahami orang lapangan: tanpa istilah teknis/Inggris."""
    import re

    messages = _user_facing_messages()
    assert len(messages) > 150   # ekstraksi benar-benar menemukan pesan
    offenders = [f"{loc}: {msg}" for loc, msg in messages if re.search(_JARGON, msg, re.IGNORECASE)]
    assert offenders == []

def test_real_app_unknown_path_and_missing_token():
    with TestClient(real_app) as client:
        unknown = client.get("/rute-yang-tidak-ada")
        no_token = client.get("/api/v1/audit-events")

    assert unknown.status_code == 404 and _error(unknown)["code"] == "NOT_FOUND"
    assert no_token.status_code == 401 and _error(no_token)["code"] == "UNAUTHENTICATED"
