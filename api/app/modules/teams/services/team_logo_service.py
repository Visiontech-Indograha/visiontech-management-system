"""
app/modules/teams/services/team_logo_service.py
Logo tim: hanya KETUA tim (karyawan TEAM_LEADER yang menjadi `leader_employee_id`) yang boleh mengganti atau
menghapus logo. SUPER_ADMIN boleh sebagai darurat (dicatat di log). Melihat/mengunduh logo: anggota tim,
PM/OM divisi tim, HR, dan SUPER_ADMIN; selain itu 404.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from typing import Any
from uuid import UUID

from app.core import storage
from app.core.errors import AppError, NotFoundError
from app.core.security import CurrentUser
from app.modules.teams.repositories.team_repository import TeamRepository
from app.shared.documents.branding import team_logo_storage_key, validate_team_logo

logger = logging.getLogger(__name__)


class TeamLogoService:
    def __init__(self, repo: TeamRepository) -> None:
        self.repo = repo

    async def _team(self, user: CurrentUser, team_id: UUID) -> Any:
        """Tim aktif dalam organisasi pengguna; lintas organisasi = 404."""
        team = await self.repo.get(team_id)
        if team is None or str(team.office_id) != str(user.organization_id):
            raise NotFoundError("Tim")
        return team

    @staticmethod
    def _is_leader(user: CurrentUser, team: Any) -> bool:
        return (user.has_role("TEAM_LEADER") and user.employee_id is not None
                and str(team.leader_employee_id) == str(user.employee_id))

    def _authorize_change(self, user: CurrentUser, team: Any) -> None:
        if self._is_leader(user, team):
            return
        if user.has_role("SUPER_ADMIN"):
            logger.warning("Logo tim %s diubah oleh SUPER_ADMIN %s (mode darurat, bukan ketua tim)",
                           team.team_id, user.user_id)
            return
        raise AppError("FORBIDDEN", "Hanya ketua tim yang dapat mengganti atau menghapus logo tim.", status=403)

    async def set_logo(self, user: CurrentUser, team_id: UUID, raw: bytes) -> str:
        """Pasang logo tim (berkas asli disimpan apa adanya) → file_id."""
        team = await self._team(user, team_id)
        self._authorize_change(user, team)
        mime, ext = validate_team_logo(raw)
        # Kunci sha256 diberi awalan tim: berkas sama dari tim lain tidak dianggap duplikat.
        sha = hashlib.sha256(b"team-logo:" + str(team.team_id).encode() + b":" + raw).digest()
        existing = await self.repo.logo_file_by_hash(team.office_id, sha)
        if existing is not None:
            file_id = str(existing.id)
        else:
            file_id = str(uuid.uuid4())
            key = team_logo_storage_key(str(team.office_id), str(team.team_id), file_id, ext)
            stored = await asyncio.to_thread(storage.upload_file, key, raw, mime)
            if not stored:
                raise AppError("STORAGE_UNAVAILABLE",
                               "Penyimpanan berkas sedang tidak tersedia. Coba lagi beberapa saat.", status=503)
            file_id = await self.repo.insert_logo_file(
                file_id=file_id, office_id=team.office_id, storage_key=key, file_name=f"logo-tim.{ext}",
                mime_type=mime, byte_size=len(raw), sha256=sha, user_id=str(user.user_id))
        await self.repo.set_logo(team.team_id, file_id)
        return file_id

    async def delete_logo(self, user: CurrentUser, team_id: UUID) -> None:
        """Kembali ke logo default. Berkas lama tetap tercatat (tidak dihapus dari storage)."""
        team = await self._team(user, team_id)
        self._authorize_change(user, team)
        await self.repo.set_logo(team.team_id, None)

    async def _can_view(self, user: CurrentUser, team: Any) -> bool:
        if user.has_role("SUPER_ADMIN", "ADMIN_HR_GA"):
            return True
        emp = str(user.employee_id) if user.employee_id else None
        if emp is None:
            return False
        if str(team.leader_employee_id) == emp or emp in (str(team.pm_id), str(team.om_id)):
            return True
        return await self.repo.is_member(team.team_id, emp)

    async def get_logo(self, user: CurrentUser, team_id: UUID) -> tuple[bytes, str]:
        """(isi berkas, mime). Tak ada / tak berhak / berkas hilang → NotFoundError (404)."""
        team = await self._team(user, team_id)
        if team.logo_file_id is None or not await self._can_view(user, team):
            raise NotFoundError("Logo tim")
        row = await self.repo.logo_file(team.logo_file_id)
        if row is None:
            raise NotFoundError("Logo tim")
        data = await asyncio.to_thread(storage.get_object_bytes, row.storage_key)
        if not data:
            raise NotFoundError("Logo tim")
        return data, row.mime_type
