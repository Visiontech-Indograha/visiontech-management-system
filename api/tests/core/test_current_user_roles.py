"""
T13 · Pemeriksaan peran memakai daftar `roles` (has_role), bukan turunan `roles[0]`.
Uji ini gagal bila pemeriksaan kembali ke `user.role == ...`.
"""
from app.core.security import CurrentUser


def _user(roles: list[str]) -> CurrentUser:
    return CurrentUser(user_id="u", organization_id="o", email="e@uji", role=roles[0], roles=roles,
                       session_id="s", permissions=[])


def test_has_role_checks_every_role_held():
    user = _user(["EMPLOYEE", "PROJECT_MANAGER"])
    assert user.has_role("PROJECT_MANAGER")
    assert user.has_role("SUPER_ADMIN", "PROJECT_MANAGER")
    assert not user.has_role("SUPER_ADMIN")
