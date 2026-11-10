"""Rute setelan sistem (hanya SUPER_ADMIN, izin manage:system_settings)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.modules.system_settings.dependencies import get_system_settings_service
from app.modules.system_settings.schemas.system_settings_schema import SystemSettingOut, SystemSettingsUpdate
from app.modules.system_settings.services.system_settings_service import SystemSettingsService

router = APIRouter(prefix="/system/settings", tags=["System"])
_ADMIN = Depends(require_permission(Permission.MANAGE_SYSTEM_SETTINGS))


@router.get("", response_model=list[SystemSettingOut])
async def list_system_settings(
    _: CurrentUser = _ADMIN, service: SystemSettingsService = Depends(get_system_settings_service),
) -> list[SystemSettingOut]:
    """Daftar setelan, nilai efektif, dan asalnya (env_force > db > env_default)."""
    return await service.list_all()


@router.put("", response_model=list[SystemSettingOut])
async def update_system_settings(
    data: SystemSettingsUpdate,
    current_user: CurrentUser = _ADMIN,
    service: SystemSettingsService = Depends(get_system_settings_service),
) -> list[SystemSettingOut]:
    """Ubah satu atau lebih setelan (boolean). 422 kunci/tipe salah; 409 SETTING_LOCKED bila dikunci env."""
    return await service.update(current_user, data.values)
