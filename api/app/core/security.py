"""
Kata sandi (argon2id, K-20) dan access token JWT EdDSA (dok 02 A-11, dok 05 §4, dok 08 §3/§7).

Kunci penandatangan JWT (tujuan `JWT_ACCESS`, terpisah dari kunci tanda tangan dokumen) dibaca
dari `JWT_PRIVATE_KEY_HEX` — 32 byte seed Ed25519 dalam hex. Di produksi nilainya disuntikkan
dari KMS/secret manager (K-05), tidak pernah disimpan di Git atau basis data.
Verifikasi hanya menerima EdDSA dengan `kid` yang dikenal: token HS256, `alg: none`, dan
kebingungan algoritma ditolak.
"""
import logging
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import settings
from app.core.time import utcnow

logger = logging.getLogger(__name__)
ph = PasswordHasher()

ACCESS_AUDIENCE = "vms-api"
ACCESS_ISSUER = "vms"
_ALGORITHM = "EdDSA"


def _load_private_key() -> Ed25519PrivateKey:
    if settings.JWT_PRIVATE_KEY_HEX:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(settings.JWT_PRIVATE_KEY_HEX))
    # Hanya layak untuk uji/dev satu proses: token tidak berlaku lagi setelah restart dan
    # tidak dikenali worker lain. Produksi WAJIB mengisi JWT_PRIVATE_KEY_HEX.
    logger.warning("JWT_PRIVATE_KEY_HEX kosong — memakai kunci sementara (hanya untuk dev/uji).")
    return Ed25519PrivateKey.generate()


_private_key = _load_private_key()
_public_key = _private_key.public_key()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def create_jwt_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    now = utcnow()
    claims = {**data, "iat": now, "exp": now + expires_delta, "aud": ACCESS_AUDIENCE, "iss": ACCESS_ISSUER}
    return jwt.encode(claims, _private_key, algorithm=_ALGORITHM, headers={"kid": settings.JWT_KID})


def verify_jwt_token(token: str) -> dict[str, Any]:
    """Klaim token bila sah; selain itu `jwt.PyJWTError` (termasuk kid asing & algoritma lain)."""
    if jwt.get_unverified_header(token).get("kid") != settings.JWT_KID:
        raise jwt.InvalidTokenError("kid tidak dikenal")
    claims: dict[str, Any] = jwt.decode(
        token,
        _public_key,
        algorithms=[_ALGORITHM],
        audience=ACCESS_AUDIENCE,
        issuer=ACCESS_ISSUER,
        options={"require": ["exp", "iat", "sub", "jti"]},
    )
    return claims
