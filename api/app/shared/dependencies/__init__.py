"""
Paket dependency bersama tingkat aplikasi.
"""
from app.shared.dependencies.common_deps import get_db_session

__all__ = [
    "get_db_session",
]

