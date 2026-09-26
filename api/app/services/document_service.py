"""
app/services/document_service.py
Dokumen pribadi — antrean verifikasi HR (P2-5, R-19). Izin verify:documents dijaga router.
"""
from __future__ import annotations

from typing import Any

from app.repositories.document_repo import DocumentRepo


class DocumentService:
    def __init__(self, repo: DocumentRepo) -> None:
        self.repo = repo

    async def pending_queue(self, org_id: str, user_id: str) -> list[Any]:
        """Dokumen menunggu verifikasi. `uploaded_by_me` → harus diperiksa petugas lain (empat mata)."""
        return await self.repo.pending_for_org(org_id, user_id)
