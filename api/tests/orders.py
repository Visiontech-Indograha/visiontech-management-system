"""
Pembantu uji order klien: order wajib memakai klien dari master, jadi uji menyiapkan klien lebih dulu.
"""
from __future__ import annotations

import uuid

from tests.conftest import sync_query


def make_client(name: str | None = None) -> str:
    """Klien aktif di master (tanpa lewat API). Kode klien acak agar tidak bentrok."""
    tag = uuid.uuid4().hex[:8]
    return str(sync_query(
        "INSERT INTO client (client_code, name) VALUES (%s, %s) RETURNING client_id",
        (f"UJI-{tag}", name or f"Klien uji {tag}"),
    )[0][0])
