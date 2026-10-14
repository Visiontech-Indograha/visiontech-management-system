"""
T-13 · Access token EdDSA (dok 02 A-11, dok 05 §4, dok 08 §3/§7, K-20).
Hanya EdDSA dengan `kid` yang dikenal yang diterima; token HS256 lama, `alg: none`, token yang
diubah, audiens salah, dan token kedaluwarsa ditolak.
"""
from __future__ import annotations

import base64
import json
from datetime import timedelta

import jwt
import pytest

from app.core import security
from app.core.security import ACCESS_AUDIENCE, create_jwt_token, verify_jwt_token
from tests.conftest import login_headers, requires_db

CLAIMS = {"sub": "00000000-0000-0000-0000-000000000001", "org": "o", "jti": "s"}


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def test_token_is_eddsa_with_kid_and_standard_claims():
    token = create_jwt_token(CLAIMS, timedelta(minutes=15))

    header = jwt.get_unverified_header(token)
    claims = verify_jwt_token(token)

    assert header["alg"] == "EdDSA"
    assert header["kid"] == security.settings.JWT_KID
    assert claims["aud"] == ACCESS_AUDIENCE
    assert {"iat", "exp", "iss"} <= set(claims)


def test_hs256_token_with_old_default_secret_is_rejected():
    forged = jwt.encode({**CLAIMS, "aud": ACCESS_AUDIENCE}, "supersecretkey_change_me_in_production",
                        algorithm="HS256", headers={"kid": security.settings.JWT_KID})

    with pytest.raises(jwt.PyJWTError):
        verify_jwt_token(forged)


def test_alg_none_is_rejected():
    unsigned = f"{_b64({'alg': 'none', 'kid': security.settings.JWT_KID})}.{_b64(CLAIMS)}."

    with pytest.raises(jwt.PyJWTError):
        verify_jwt_token(unsigned)


def test_tampered_payload_is_rejected():
    header, _, signature = create_jwt_token(CLAIMS, timedelta(minutes=15)).split(".")
    tampered = f"{header}.{_b64({**CLAIMS, 'sub': 'penyusup'})}.{signature}"

    with pytest.raises(jwt.PyJWTError):
        verify_jwt_token(tampered)


def test_expired_token_is_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_jwt_token(create_jwt_token(CLAIMS, timedelta(seconds=-1)))


def test_unknown_kid_is_rejected():
    token = create_jwt_token(CLAIMS, timedelta(minutes=15))
    _, payload, signature = token.split(".")
    other_kid = f"{_b64({'alg': 'EdDSA', 'typ': 'JWT', 'kid': 'kunci-lain'})}.{payload}.{signature}"

    with pytest.raises(jwt.PyJWTError):
        verify_jwt_token(other_kid)


def test_wrong_audience_is_rejected(monkeypatch):
    monkeypatch.setattr(security, "ACCESS_AUDIENCE", "layanan-lain")
    token = create_jwt_token(CLAIMS, timedelta(minutes=15))
    monkeypatch.undo()

    with pytest.raises(jwt.InvalidAudienceError):
        verify_jwt_token(token)


@requires_db
def test_forged_hs256_token_gets_401_from_api(client, make_user):
    user = make_user("ADMIN")
    real = login_headers(client, user)["Authorization"].removeprefix("Bearer ")
    claims = verify_jwt_token(real)
    forged = jwt.encode(claims, "supersecretkey_change_me_in_production", algorithm="HS256",
                        headers={"kid": security.settings.JWT_KID})

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_file_access_ticket_roundtrip():
    from app.core.security import create_file_access_ticket, verify_file_access_ticket

    ticket = create_file_access_ticket("user-1", "file-1", "org-1", "view")
    claims = verify_file_access_ticket(ticket, "file-1")
    assert claims is not None
    assert claims["sub"] == "user-1"
    assert claims["fid"] == "file-1"
    assert claims["org"] == "org-1"

    # Mismatched file_id must be rejected
    assert verify_file_access_ticket(ticket, "file-2") is None
