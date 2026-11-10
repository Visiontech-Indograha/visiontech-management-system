"""Penyiapan awal: admin pertama hanya bila belum ada SUPER_ADMIN aktif; sesudahnya terkunci (409)."""
from __future__ import annotations

import asyncio
import hmac
import logging

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.hard_delete import write_delete_audit
from app.core.security import hash_password
from app.modules.setup.repositories.setup_repository import SetupRepository
from app.modules.setup.schemas.setup_schema import SetupAdminIn, SetupAdminOut, SetupStatusOut

logger = logging.getLogger(__name__)
SETUP_TOKEN_MIN = 24


def _token_enabled() -> bool:
    return len(settings.SETUP_TOKEN) >= SETUP_TOKEN_MIN


class SetupService:
    def __init__(self, repo: SetupRepository, ip: str = "-") -> None:
        self.repo = repo
        self.ip = ip

    async def status(self) -> SetupStatusOut:
        return SetupStatusOut(needs_setup=not await self.repo.has_active_super_admin(), enabled=_token_enabled())

    async def create_admin(self, data: SetupAdminIn) -> SetupAdminOut:
        if not _token_enabled():
            raise NotFoundError("Halaman")  # endpoint mati
        if not hmac.compare_digest(data.setup_token.encode(), settings.SETUP_TOKEN.encode()):
            logger.warning("penyiapan awal: kode salah dari ip=%s", self.ip)
            raise AppError("SETUP_TOKEN_INVALID", "Kode penyiapan salah.", status=403)

        await self.repo.lock()  # permintaan bersamaan antre di sini; yang kedua melihat admin yang baru dibuat
        if await self.repo.has_active_super_admin():
            raise AppError("SETUP_LOCKED", "Instalasi ini sudah disiapkan. Silakan masuk.", status=409)
        email = data.email.strip().lower()
        if await self.repo.email_taken(email):
            raise AppError("EMAIL_TAKEN", "Email ini sudah dipakai akun lain.", status=409)

        password_hash = await asyncio.to_thread(hash_password, data.password)
        office_id = await self.repo.first_or_new_office()
        user_id = await self.repo.insert_admin(office_id, data.full_name.strip(), email, password_hash)
        await write_delete_audit(
            self.repo.db, actor_user_id=str(user_id), actor_role="SUPER_ADMIN", actor_email=email,
            entity_type="users", entity_id=user_id, action="SETUP_ADMIN_CREATED",
            detail={"ip": self.ip, "office_id": str(office_id)},
        )
        logger.info("penyiapan awal: admin pertama dibuat user_id=%s", user_id)
        return SetupAdminOut(user_id=str(user_id), email=email)
