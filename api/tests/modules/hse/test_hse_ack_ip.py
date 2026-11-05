"""
api/tests/modules/hse/test_hse_ack_ip.py

IP pada catatan persetujuan HSE memakai helper client_ip (hormati TRUSTED_PROXY_IPS),
bukan X-Forwarded-For mentah dari klien. Tanpa DB: service dipalsukan.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from starlette.requests import Request

from app.core.config import settings
from app.modules.hse.controllers.hse_controller import HseController


class _FakeService:
    def __init__(self) -> None:
        self.ip_address: str | None = None

    async def acknowledge_campaign(self, **kwargs: Any) -> dict[str, bool]:
        self.ip_address = kwargs["ip_address"]
        return {"ok": True}


def _request(peer: str, xff: str | None = None) -> Request:
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
            "client": (peer, 40000),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def _ack_ip(monkeypatch: pytest.MonkeyPatch, peer: str, xff: str | None, trusted: str) -> str | None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", trusted)
    service = _FakeService()
    controller = HseController(service)  # type: ignore[arg-type]
    asyncio.run(
        controller.acknowledge_campaign(
            campaign_id=uuid4(),
            current_user=None,  # type: ignore[arg-type]
            data=None,  # type: ignore[arg-type]
            request=_request(peer, xff),
        )
    )
    return service.ip_address


def test_xff_dari_klien_langsung_diabaikan(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tanpa proxy tepercaya, X-Forwarded-For palsu tidak boleh masuk catatan audit.
    ip = _ack_ip(monkeypatch, "198.51.100.9", "203.0.113.7", trusted="")
    assert ip == "198.51.100.9"


def test_xff_dibaca_hanya_dari_proxy_tepercaya(monkeypatch: pytest.MonkeyPatch) -> None:
    ip = _ack_ip(monkeypatch, "10.0.0.5", "203.0.113.7, 10.0.0.9", trusted="10.0.0.0/8")
    assert ip == "203.0.113.7"


def test_xff_palsu_di_depan_proxy_tidak_dipercaya(monkeypatch: pytest.MonkeyPatch) -> None:
    # Klien menyisipkan IP palsu di kiri; hop kanan (proxy) membuktikan klien sebenarnya.
    ip = _ack_ip(monkeypatch, "10.0.0.5", "1.2.3.4, 198.51.100.9", trusted="10.0.0.0/8")
    assert ip == "198.51.100.9"
