"""
Inventaris rute aplikasi untuk uji penjaga. Memakai skema OpenAPI (API publik FastAPI), karena
sejak FastAPI 0.14x `app.routes` menyimpan router yang di-include sebagai objek malas
(`_IncludedRouter`) — iterasi `app.routes` tidak lagi melihat rute di bawah awalan.
"""
from __future__ import annotations

from app.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def all_routes() -> list[tuple[str, str]]:
    """Semua (METODE, jalur lengkap) yang dilayani aplikasi, terurut."""
    return sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in HTTP_METHODS
    )
