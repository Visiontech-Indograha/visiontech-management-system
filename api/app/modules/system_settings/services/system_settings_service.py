"""Setelan sistem: baca (efektif + asal) dan ubah (validasi kunci/tipe, kunci env, audit sebelum/sesudah)."""
from __future__ import annotations

import uuid
from typing import Any

from app.core import system_settings
from app.core.errors import AppError, ValidationError
from app.core.hard_delete import write_delete_audit
from app.core.security import CurrentUser
from app.modules.system_settings.repositories.system_settings_repository import SystemSettingsRepository
from app.modules.system_settings.schemas.system_settings_schema import SystemSettingOut

_NS = uuid.UUID("6f1f5a64-7b8e-4a53-9c1d-0d6a3a1e5b10")


class SystemSettingsService:
    def __init__(self, repo: SystemSettingsRepository) -> None:
        self.repo = repo

    async def list_all(self) -> list[SystemSettingOut]:
        rows = await self.repo.rows()
        known = {k: v for k, (v, _) in rows.items() if k in system_settings.SPECS and isinstance(v, bool)}
        system_settings.set_cached(known)
        force = system_settings.forced()
        return [
            SystemSettingOut(
                key=spec.key, label=spec.label, description=spec.description,
                value=system_settings.get_bool(spec.key), source=system_settings.source_of(spec.key),  # type: ignore[arg-type]
                env_default=system_settings.env_default(spec.key), locked=spec.key in force,
                updated_at=rows[spec.key][1] if spec.key in rows else None,
            )
            for spec in system_settings.SPECS.values()
        ]

    async def update(self, actor: CurrentUser, values: dict[str, bool]) -> list[SystemSettingOut]:
        unknown = sorted(k for k in values if k not in system_settings.SPECS)
        if unknown:
            raise ValidationError(f"Setelan tidak dikenal: {', '.join(unknown)}.")
        locked = sorted(k for k in values if k in system_settings.forced())
        if locked:
            raise AppError(
                "SETTING_LOCKED",
                f"Setelan dikunci oleh pengaturan pemasangan dan tidak bisa diubah di sini: {', '.join(locked)}.",
                status=409,
            )
        keys = sorted(values)
        previous = await self.repo.lock_rows(keys)
        for key in keys:
            before = previous[key] if isinstance(previous.get(key), bool) else system_settings.env_default(key)
            if key in previous and previous[key] == values[key]:
                continue  # tidak berubah: tanpa tulis dan tanpa audit
            await self.repo.upsert(key, values[key], actor.user_id)
            await self._audit(actor, key, before, values[key])
        system_settings.set_cached(values)
        return await self.list_all()

    async def _audit(self, actor: CurrentUser, key: str, before: Any, after: Any) -> None:
        await write_delete_audit(
            self.repo.db, actor_user_id=actor.user_id, actor_role=actor.role, actor_email=actor.email,
            entity_type="system_setting", entity_id=uuid.uuid5(_NS, key), action="SYSTEM_SETTING_UPDATE",
            detail={"key": key, "before": before, "after": after},
        )
