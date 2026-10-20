"""
Uji unit untuk batas sesi 24 jam, batas 4 perangkat, notifikasi login baru, dan logout aman.
"""
from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.core.events import broker
from app.core.security import create_jwt_token, verify_jwt_token
from app.modules.auth.services.auth_service import AuthService, ClientInfo


def test_jwt_contains_auth_time_claim():
    """Memastikan token JWT yang diterbitkan membawa klaim auth_time."""
    user_id = str(uuid4())
    org_id = str(uuid4())
    session_id = str(uuid4())
    now_epoch = int(time.time())

    # Token dengan auth_time default
    token = create_jwt_token(
        {"sub": user_id, "org": org_id, "jti": session_id},
        expires_delta=timedelta(minutes=15),
    )
    claims = verify_jwt_token(token)
    assert "auth_time" in claims
    assert isinstance(claims["auth_time"], int)
    assert abs(claims["auth_time"] - now_epoch) <= 5

    # Token dengan auth_time spesifik (misal dari rotasi sesi)
    custom_auth_time = now_epoch - 3600
    token2 = create_jwt_token(
        {"sub": user_id, "org": org_id, "jti": session_id, "auth_time": custom_auth_time},
        expires_delta=timedelta(minutes=15),
    )
    claims2 = verify_jwt_token(token2)
    assert claims2["auth_time"] == custom_auth_time


@pytest.mark.anyio
async def test_max_4_devices_limit_enforced():
    """Memastikan login dari perangkat ke-5 ditolak dengan status 403 MAX_DEVICES_REACHED."""
    service = AuthService(AsyncMock(), AsyncMock())

    user = MagicMock()
    user.id = uuid4()
    user.organization_id = uuid4()
    user.is_active = True
    user.password_hash = "$argon2id$mock"
    user.role = "field"

    service.sessions.failed_logins = AsyncMock(return_value=MagicMock(locked_until=None))
    service.users.find_by_login = AsyncMock(return_value=user)
    service.users.get_attendance_mode = AsyncMock(return_value="FIELD")
    service._act_as = AsyncMock()

    # Skenario 1: Sudah ada 4 perangkat aktif, login dari perangkat baru (fingerprint beda)
    service.sessions.find_active_family_by_fingerprint = AsyncMock(return_value=None)
    service.sessions.count_active_devices = AsyncMock(return_value=4)

    client = ClientInfo(ip="192.168.1.10", user_agent="Mozilla/5.0", device_label="Device 5", fingerprint="fp-5")

    with patch("app.modules.auth.services.auth_service.verify_password", return_value=True):
        with pytest.raises(AppError) as exc_info:
            await service.login("staf@example.com", "Secret123!", client, platform="mobile")
        assert exc_info.value.code == "MAX_DEVICES_REACHED"
        assert exc_info.value.status == 403

    # Skenario 2: Sudah ada 4 perangkat aktif, tetapi login ulang dari perangkat yang sama (fingerprint sama)
    old_family = uuid4()
    service.sessions.find_active_family_by_fingerprint = AsyncMock(return_value=old_family)
    service.sessions.revoke_family = AsyncMock()
    service.sessions.record_login_attempt = AsyncMock()
    service._start_session = AsyncMock(return_value=MagicMock(access_token="tok", refresh_token="ref"))

    with patch("app.modules.auth.services.auth_service.verify_password", return_value=True):
        tokens = await service.login("staf@example.com", "Secret123!", client, platform="mobile")
        assert tokens.access_token == "tok"
        service.sessions.revoke_family.assert_awaited_once_with(
            user.id, old_family, "Masuk ulang pada perangkat yang sama"
        )


@pytest.mark.anyio
async def test_security_login_event_broadcast():
    """Memastikan saat login berhasil, event SSE topik security dipublikasikan ke broker."""
    service = AuthService(AsyncMock(), AsyncMock())

    user = MagicMock()
    user.id = uuid4()
    user.organization_id = uuid4()
    user.is_active = True
    user.password_hash = "$argon2id$mock"
    user.role = "ADMIN"

    service.sessions.failed_logins = AsyncMock(return_value=MagicMock(locked_until=None))
    service.users.find_by_login = AsyncMock(return_value=user)
    service.users.get_attendance_mode = AsyncMock(return_value=None)
    service._act_as = AsyncMock()
    service.sessions.find_active_family_by_fingerprint = AsyncMock(return_value=None)
    service.sessions.count_active_devices = AsyncMock(return_value=1)
    service.sessions.record_login_attempt = AsyncMock()
    service._start_session = AsyncMock(return_value=MagicMock(access_token="tok", refresh_token="ref"))

    published_events = []
    with (
        patch.object(broker, "publish", side_effect=lambda users, ev: published_events.append((users, ev))),
        patch("app.modules.auth.services.auth_service.verify_password", return_value=True),
    ):
        client = ClientInfo(ip="10.0.0.1", user_agent="Chrome", device_label="Laptop Baru")
        await service.login("admin@example.com", "Secret123!", client, platform="web")

    assert len(published_events) == 1
    users, event = published_events[0]
    assert users == [str(user.id)]
    assert event["topic"] == "security"
    assert event["data"]["type"] == "SECURITY_LOGIN"
    assert "Laptop Baru" in event["data"]["body"]


@pytest.mark.anyio
async def test_refresh_token_expired_does_not_trigger_discord_alert():
    """Memastikan token refresh yang kedaluwarsa waktu normal tidak mengirim alert pencurian ke Discord."""
    service = AuthService(AsyncMock(), AsyncMock())

    # Database mengembalikan reused = False, session_id = None (karena kedaluwarsa normal)
    service.sessions.rotate = AsyncMock(
        return_value=MagicMock(session_id=None, user_id=uuid4(), refresh_token=None, reused=False)
    )

    client = ClientInfo(ip="192.168.1.1", user_agent="Mozilla")

    with patch("app.modules.auth.services.auth_service.send_security_alert") as mock_alert:
        with pytest.raises(AppError) as exc_info:
            await service.refresh("expired-token", client)
        assert exc_info.value.code == "INVALID_TOKEN"
        # TIDAK memanggil send_security_alert
        mock_alert.assert_not_called()
