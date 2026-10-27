"""
app/modules/work_completion/repositories/work_completion_sign_repository.py
Akses data tanda tangan digital BAST, foto realisasi, dan hash verifikasi.
"""
from __future__ import annotations

import json
from uuid import UUID

from app.core.repository import BaseRepository


class WorkCompletionSignRepository(BaseRepository):
    """Query dan pembaruan tanda tangan BAST dan bukti foto."""

    async def sign_completion(
        self,
        *,
        completion_id: UUID | str,
        signer_id: UUID | str,
        as_leader: bool,
        signature_key: str,
        summary_notes: str | None = None,
        obstacles: str | None = None,
        photos: list[str] | None = None,
    ) -> None:
        """Tanda tangan ketua (boleh diulang sebelum PM; sidik direset) atau PM (order selesai)."""
        if as_leader:
            sql = """
                UPDATE work_completion
                SET leader_signer_id = CAST(:signer_id AS uuid),
                    leader_signature_path = :sig_key,
                    leader_signed_at = NOW(),
                    summary_notes = COALESCE(:summary_notes, summary_notes),
                    obstacles = COALESCE(:obstacles, obstacles),
                    realization_photos_json = COALESCE(CAST(:photos AS jsonb), realization_photos_json),
                    signature_hash = NULL,
                    update_at = NOW()
                WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL AND pm_signed_at IS NULL
            """
        else:
            sql = """
                UPDATE work_completion
                SET pm_signer_id = CAST(:signer_id AS uuid),
                    pm_signature_path = :sig_key,
                    pm_signed_at = NOW(),
                    order_status = 'COMPLETED',
                    update_at = NOW()
                WHERE completion_id = CAST(:id AS uuid) AND delete_at IS NULL AND pm_signed_at IS NULL
                  AND leader_signed_at IS NOT NULL
            """
        await self.execute(
            sql,
            {
                "id": str(completion_id),
                "signer_id": str(signer_id),
                "sig_key": signature_key,
                "summary_notes": summary_notes,
                "obstacles": obstacles,
                "photos": json.dumps(photos) if photos else None,
            },
        )

    async def remove_photo(self, completion_id: UUID | str, file_id: str) -> bool:
        """Lepas satu foto realisasi (format lama: id string; baru: {file_id}). True bila ada yang terhapus."""
        removed = await self.scalar(
            """
            UPDATE work_completion SET realization_photos_json = COALESCE((
                SELECT jsonb_agg(e) FROM jsonb_array_elements(realization_photos_json) e
                WHERE COALESCE(e->>'file_id', e #>> '{}') <> :f), '[]'::jsonb), update_at = now()
            WHERE completion_id = CAST(:id AS uuid)
              AND EXISTS (SELECT 1 FROM jsonb_array_elements(realization_photos_json) e
                          WHERE COALESCE(e->>'file_id', e #>> '{}') = :f)
            RETURNING 1
            """,
            {"id": str(completion_id), "f": file_id},
        )
        return bool(removed)

    async def set_signature_hash(self, completion_id: UUID | str, signature_hash: str) -> None:
        await self.execute(
            "UPDATE work_completion SET signature_hash = :h WHERE completion_id = CAST(:id AS uuid)",
            {"id": str(completion_id), "h": signature_hash},
        )

    async def existing_images(self, file_ids: list[str]) -> int:
        """Jumlah id yang benar-benar berkas gambar terunggah (foto realisasi BAST)."""
        if not file_ids:
            return 0
        count = await self.scalar(
            "SELECT COUNT(*) FROM file_object WHERE id = ANY(CAST(:ids AS uuid[])) AND mime_type LIKE 'image/%'",
            {"ids": file_ids},
        )
        return int(count or 0)
