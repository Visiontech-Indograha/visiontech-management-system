"""T1 (docs/diagram): ADMIN lama tidak boleh melewati izin hapus permanen (DELETE_ANY khusus SUPER_ADMIN)."""
import asyncio

import pytest

from app.api.deps import require_any_permission, require_permission
from app.core.errors import AppError
from app.core.permissions import Permission
from app.core.security import CurrentUser


def _user(role: str, perms: list[str]) -> CurrentUser:
    return CurrentUser(user_id="u", organization_id="o", email="a@b.c", role=role, roles=[role], session_id="s",
                       permissions=perms)


def _run(dep, user):
    return asyncio.run(dep.__wrapped__(user) if hasattr(dep, "__wrapped__") else dep(user))


def test_admin_still_passes_ordinary_permissions():
    assert _run(require_permission(Permission.CREATE_PLAN), _user("ADMIN", []))


def test_admin_cannot_hard_delete_without_the_permission():
    with pytest.raises(AppError) as exc:
        _run(require_permission(Permission.DELETE_ANY), _user("ADMIN", []))
    assert exc.value.status == 403
    with pytest.raises(AppError):
        _run(require_any_permission(Permission.DELETE_ANY), _user("ADMIN", []))


def test_super_admin_with_permission_can_hard_delete():
    assert _run(require_permission(Permission.DELETE_ANY), _user("SUPER_ADMIN", [Permission.DELETE_ANY.value]))
