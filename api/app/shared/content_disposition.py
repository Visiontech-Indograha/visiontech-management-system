"""Header Content-Disposition yang aman untuk nama berkas non-ASCII (RFC 6266/5987).

Header HTTP hanya boleh latin-1; nama seperti "Replacement CCTV — Gudang Duri.jpg" membuat server 500.
Nama asli dikirim lewat `filename*` (UTF-8, ter-encode), cadangan ASCII lewat `filename`.
"""
from __future__ import annotations

import unicodedata
from urllib.parse import quote


def content_disposition(kind: str, name: str) -> str:
    """`kind` = "inline" | "attachment"."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.replace('"', "").replace("\\", "") or "berkas"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name, safe='')}"
