"""
app/modules/accounts/services/account_service.py
Akun login karyawan (M1-01, R-20): HR/admin membuat akun, mereset password, menonaktifkan & mengaktifkan.
Izin manage:users dijaga router; batas organisasi & aturan di sini. Password sementara hanya dikembalikan
sekali dan tidak pernah disimpan selain hash argon2.
"""

from __future__ import annotations

import asyncio
import secrets
import string
from types import SimpleNamespace
from typing import Any

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.hard_delete import purge_row, write_delete_audit
from app.core.permissions import SystemRole
from app.core.security import CurrentUser, hash_password
from app.modules.auth.repositories.auth_session_repository import CRUDSession
from app.modules.auth.repositories.auth_user_repository import CRUDUser
from app.modules.employees.repositories.employee_repository import CRUDEmployee

_ALPHABET = string.ascii_letters + string.digits

# Peran lapangan yang boleh dipilih pada akun karyawan, dan siapa yang boleh memilihnya (HR & SUPER_ADMIN saja).
FIELD_ROLES = ("EMPLOYEE", "TEAM_LEADER")
_ACCOUNT_MANAGERS = (SystemRole.SUPER_ADMIN, SystemRole.ADMIN_HR_GA)


def _require_account_manager(actor: CurrentUser) -> None:
    if not any(actor.has_role(role) for role in _ACCOUNT_MANAGERS):
        raise ForbiddenError("Hanya HR/Admin atau SUPER_ADMIN yang dapat mengatur peran akun karyawan.")


def temporary_password() -> str:
    """12 karakter acak + jaminan huruf & angka (kebijakan password web: min 8, huruf + angka)."""
    return (
        "".join(secrets.choice(_ALPHABET) for _ in range(10))
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
    )


class AccountService:
    """Layanan untuk mengelola akun autentikasi karyawan, termasuk pembuatan akun dan reset kata sandi."""

    def __init__(self, users: CRUDUser, employees: CRUDEmployee, sessions: CRUDSession) -> None:
        self.users, self.employees, self.sessions = users, employees, sessions

    async def _employee(self, employee_id: Any, org_id: str) -> Any:
        # Mengunci data karyawan untuk mencegah perubahan berbarengan (race conditions) saat mutasi akun.
        emp = await self.employees.lock(employee_id, org_id)
        if emp is None or emp.deleted:
            raise NotFoundError("Karyawan")
        return emp

    async def _account(self, employee_id: Any, org_id: str) -> Any:
        await self._employee(employee_id, org_id)
        # Memastikan karyawan telah memiliki akun sebelum melakukan tindakan yang membutuhkan akun eksisting.
        account = await self.users.account_of_employee(employee_id)
        if account is None:
            raise NotFoundError("Akun")
        return account

    async def _with_login_state(self, account: Any) -> Any:
        """Akun + status percobaan masuknya (kegagalan beruntun & kunci) dari jejak audit login."""
        if account is None:
            return None
        state = await self.sessions.failed_logins(str(account.login))
        return SimpleNamespace(**account._mapping, failures=state.failures, locked_until=state.locked_until)

    async def account(self, employee_id: Any, org_id: str) -> Any:
        """
        Mengambil detail akun dari karyawan.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi (untuk pengecekan izin).

        Returns:
            Data akun karyawan terkait jika ada.
        """
        await self._employee(employee_id, org_id)
        return await self._with_login_state(await self.users.account_of_employee(employee_id))

    async def create(
        self, employee_id: Any, actor: CurrentUser, login: str, system_role: str = "EMPLOYEE"
    ) -> tuple[Any, str]:
        """
        Membuat akun login baru untuk karyawan yang ada.

        Args:
            employee_id: ID karyawan.
            actor: Pengguna yang membuat akun (HR/SUPER_ADMIN).
            login: Alamat email login.
            system_role: Peran lapangan (EMPLOYEE atau TEAM_LEADER).

        Returns:
            Tuple dari (Data akun, password sementara).
        """
        _require_account_manager(actor)
        if system_role not in FIELD_ROLES:
            raise AppError("ROLE_NOT_FIELD", "Peran akun hanya Karyawan Lapangan atau Team Leader.", status=422)
        org_id = actor.organization_id
        emp = await self._employee(employee_id, org_id)
        # Aturan bisnis: Karyawan yang nonaktif tidak boleh mendapatkan akses.
        if not emp.is_active:
            raise AppError("EMPLOYEE_INACTIVE", "Karyawan sudah nonaktif; akun tidak dapat dibuat.", status=409)
        if await self.users.account_of_employee(employee_id) is not None:
            raise AppError("ACCOUNT_EXISTS", "Karyawan ini sudah punya akun.", status=409)

        # Pengecekan keunikan email secara global untuk mencegah tabrakan kredensial.
        if await self.users.login_taken(org_id, login):
            raise AppError("LOGIN_TAKEN", "Email login sudah dipakai akun lain.", status=409)

        password = temporary_password()
        password_hash = await asyncio.to_thread(hash_password, password)
        row = await self.users.create_for_employee(org_id, employee_id, login, password_hash, system_role)
        await write_delete_audit(
            self.users.db, actor_user_id=actor.user_id, actor_role=actor.role, actor_email=actor.email,
            entity_type="users", entity_id=row.id, action="ACCOUNT_CREATE",
            detail={"employee_id": str(employee_id), "system_role": system_role},
        )
        return row, password

    async def set_field_role(self, employee_id: Any, actor: CurrentUser, system_role: str) -> Any:
        """
        Mengubah peran lapangan akun (EMPLOYEE ↔ TEAM_LEADER). Peran kantor/admin tidak bisa diatur di sini, dan
        ketua tim yang masih memimpin tim tidak bisa diturunkan. Perubahan dicatat di audit.
        """
        _require_account_manager(actor)
        if system_role not in FIELD_ROLES:
            raise AppError("ROLE_NOT_FIELD", "Peran akun hanya Karyawan Lapangan atau Team Leader.", status=422)
        account = await self._account(employee_id, actor.organization_id)
        if account.role not in FIELD_ROLES:
            raise AppError(
                "ROLE_NOT_FIELD", "Akun ini bukan peran lapangan; peran kantor tidak diubah dari sini.", status=409
            )
        if account.role == system_role:
            return await self._with_login_state(account)
        if system_role == "EMPLOYEE" and await self.users.leads_a_team(employee_id):
            raise AppError(
                "LEADER_ACTIVE_TEAM",
                "Karyawan ini masih memimpin tim; ganti ketua tim sebelum menurunkan perannya.",
                status=409,
            )
        await self.users.set_system_role(account.id, system_role)
        await write_delete_audit(
            self.users.db, actor_user_id=actor.user_id, actor_role=actor.role, actor_email=actor.email,
            entity_type="users", entity_id=account.id, action="ROLE_CHANGE",
            detail={"employee_id": str(employee_id), "from": account.role, "to": system_role},
        )
        return await self._with_login_state(await self.users.account_of_employee(employee_id))

    async def reset_password(self, employee_id: Any, org_id: str) -> tuple[Any, str]:
        """
        Mereset password akun menjadi password sementara dan mencabut semua sesi aktif.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi.

        Returns:
            Tuple dari (Data akun, password sementara yang baru).
        """
        account = await self._account(employee_id, org_id)
        password = temporary_password()
        password_hash = await asyncio.to_thread(hash_password, password)
        await self.users.update_password_hash(account.id, password_hash)
        # Menghentikan paksa (revoke) semua sesi terbuka agar pemilik tidak menggunakan sesi yang rentan (compromised).
        await self.sessions.revoke_all_for_user(account.id, "PASSWORD_RESET")
        # Reset oleh HR/admin sekaligus membuka kunci kegagalan login.
        await self.sessions.record_login_attempt(
            str(account.login), None, True, "PASSWORD_RESET", user_id=account.id, action="LOGIN_UNLOCKED"
        )
        return account, password

    async def delete_account(self, employee_id: Any, actor: CurrentUser) -> None:
        """Hapus permanen akun login (bukan data karyawannya). Admin tidak boleh menghapus akunnya sendiri."""
        account = await self._account(employee_id, actor.organization_id)
        if str(account.id) == actor.user_id:
            raise AppError("CANNOT_DELETE_SELF", "Anda tidak bisa menghapus akun Anda sendiri.", status=409)
        await purge_row(self.users.db, "users", "user_id", account.id)
        await write_delete_audit(
            self.users.db, actor_user_id=actor.user_id,
            actor_role=actor.role,
            actor_email=actor.email, entity_type="users", entity_id=account.id,
            detail={"employee_id": str(employee_id)},
        )

    async def set_active(self, employee_id: Any, org_id: str, active: bool) -> Any:
        """
        Mengaktifkan atau menonaktifkan akun login karyawan.

        Args:
            employee_id: ID karyawan.
            org_id: ID organisasi.
            active: Flag True/False status.

        Returns:
            Data akun setelah diperbarui.
        """
        account = await self._account(employee_id, org_id)
        if active:
            emp = await self._employee(employee_id, org_id)
            # Menjaga konsistensi bisnis: Akun tidak boleh aktif jika status pekerjanya sudah nonaktif.
            if not emp.is_active:
                raise AppError("EMPLOYEE_INACTIVE", "Karyawan sudah nonaktif; akun tidak dapat diaktifkan.", status=409)
        await self.users.set_active(account.id, active)
        if not active:
            # Mencabut semua sesi terbuka sebagai konsekuensi keamanan penonaktifan akun.
            await self.sessions.revoke_all_for_user(account.id, "ACCOUNT_DEACTIVATED")
        return await self._with_login_state(await self.users.account_of_employee(employee_id))

    # ── Kendali admin: sesi perangkat, buka kunci, ganti email login, hapus akun ──────────────────

    async def _audit(self, actor: CurrentUser, account: Any, action: str, detail: dict[str, Any]) -> None:
        await write_delete_audit(
            self.users.db, actor_user_id=actor.user_id, actor_role=actor.role, actor_email=actor.email,
            entity_type="users", entity_id=account.id, action=action, detail=detail,
        )

    async def sessions_of(self, employee_id: Any, org_id: str) -> list[Any]:
        """Sesi perangkat aktif milik akun karyawan (dilihat HR/admin)."""
        account = await self._account(employee_id, org_id)
        return await self.sessions.list_active(account.id)

    async def revoke_session(self, employee_id: Any, actor: CurrentUser, session_id: Any) -> None:
        """Cabut satu sesi perangkat milik akun ini. Sesi milik akun lain → 404."""
        account = await self._account(employee_id, actor.organization_id)
        if not await self.sessions.revoke_session(str(account.id), str(session_id), "ADMIN_REVOKE"):
            raise NotFoundError("Sesi")
        await self._audit(
            actor, account, "SESSION_REVOKE", {"employee_id": str(employee_id), "session_id": str(session_id)}
        )

    async def revoke_all_sessions(self, employee_id: Any, actor: CurrentUser, action: str) -> int:
        """Paksa keluar semua perangkat akun. `action` membedakan jejak audit: paksa keluar vs reset slot perangkat."""
        account = await self._account(employee_id, actor.organization_id)
        revoked = await self.sessions.revoke_all_for_user(account.id, action)
        await self._audit(actor, account, action, {"employee_id": str(employee_id), "revoked": revoked})
        return revoked

    async def unlock(self, employee_id: Any, actor: CurrentUser) -> Any:
        """Buka kunci akun yang terkunci karena gagal masuk berulang. Riwayat gagal masuk dianggap selesai."""
        account = await self._account(employee_id, actor.organization_id)
        await self.sessions.record_login_attempt(
            str(account.login), None, True, "ADMIN_UNLOCK", user_id=account.id, action="LOGIN_UNLOCKED"
        )
        await self._audit(actor, account, "ACCOUNT_UNLOCK", {"employee_id": str(employee_id)})
        return await self._with_login_state(await self.users.account_of_employee(employee_id))

    async def change_login(self, employee_id: Any, actor: CurrentUser, login: str) -> Any:
        """
        Ganti email login akun. Email harus unik di seluruh sistem; sesi lama dicabut agar kredensial lama
        tidak lagi dipakai. Email yang sama dengan sekarang tidak mengubah apa pun.
        """
        account = await self._account(employee_id, actor.organization_id)
        old = str(account.login)
        if login == old:
            return await self._with_login_state(account)
        if await self.users.login_taken(actor.organization_id, login):
            raise AppError("LOGIN_TAKEN", "Email login sudah dipakai akun lain.", status=409)
        await self.users.set_login(account.id, login)
        revoked = await self.sessions.revoke_all_for_user(account.id, "LOGIN_CHANGED")
        await self._audit(
            actor, account, "ACCOUNT_LOGIN_CHANGE",
            {"employee_id": str(employee_id), "from": old, "to": login, "revoked": revoked},
        )
        return await self._with_login_state(await self.users.account_of_employee(employee_id))
