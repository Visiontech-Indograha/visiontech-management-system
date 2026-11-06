"""Caddyfile web harus mempercayai proxy di depannya agar X-Forwarded-For klien tidak ditimpa."""

from pathlib import Path

CADDYFILE = Path(__file__).resolve().parents[3] / "web" / "Caddyfile"


def test_caddy_mempercayai_proxy_depan() -> None:
    teks = CADDYFILE.read_text(encoding="utf-8")
    assert "trusted_proxies static" in teks
    assert "private_ranges" in teks
    assert "100.64.0.0/10" in teks  # Tailscale
