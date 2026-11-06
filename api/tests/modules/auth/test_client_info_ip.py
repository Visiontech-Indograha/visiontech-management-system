"""
api/tests/modules/auth/test_client_info_ip.py

IP sesi (ClientInfo) memakai client_ip: X-Forwarded-For dipercaya hanya dari proxy tepercaya.
Tanpa DB.
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.core.config import settings
from app.modules.auth.controllers.auth_login_controller import AuthLoginController


def _request(peer: str | None, xff: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "query_string": b"",
            "headers": headers,
            "client": (peer, 1234) if peer else None,
        }
    )


@pytest.fixture
def trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "172.20.0.0/16")


def test_ip_sesi_dari_xff_bila_peer_tepercaya(trusted: None) -> None:
    info = AuthLoginController.extract_client_info(_request("172.20.0.5", "203.0.113.9"))
    assert info.ip == "203.0.113.9"


def test_ip_sesi_abaikan_xff_palsu_bila_peer_tak_tepercaya(trusted: None) -> None:
    info = AuthLoginController.extract_client_info(_request("198.51.100.7", "203.0.113.9"))
    assert info.ip == "198.51.100.7"


def test_ip_sesi_none_bila_tanpa_peer(trusted: None) -> None:
    assert AuthLoginController.extract_client_info(_request(None)).ip is None
