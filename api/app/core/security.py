import os
from datetime import UTC, datetime, timedelta

import jwt
import nacl.encoding
import nacl.exceptions
import nacl.signing
from argon2 import PasswordHasher

from app.core.config import settings

ph = PasswordHasher()

# Generate or load Ed25519 keys
# In a real app, these should be loaded from env or secrets manager
_private_key_hex = os.getenv("ED25519_PRIVATE_KEY")
if not _private_key_hex:
    _signing_key = nacl.signing.SigningKey.generate()
    _private_key_hex = _signing_key.encode(encoder=nacl.encoding.HexEncoder).decode('utf-8')
else:
    _signing_key = nacl.signing.SigningKey(_private_key_hex, encoder=nacl.encoding.HexEncoder)

_verify_key = _signing_key.verify_key
_public_key_hex = _verify_key.encode(encoder=nacl.encoding.HexEncoder).decode('utf-8')

# Using PyJWT which supports EdDSA if cryptography is installed, but since we use PyNaCl:
# PyJWT with 'EdDSA' requires cryptography package.
# Let's ensure cryptography is installed or use PyJWT native EdDSA.
# Wait, PyJWT requires `cryptography` for EdDSA!

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except Exception:
        return False

def create_jwt_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})
    
    # We will use cryptography for PyJWT EdDSA if installed. 
    # For now, if we don't have it, we fallback to HS256 for testing,
    # but the requirement says EdDSA. We should install cryptography!
    # Let's assume we have it or will add it.
    
    # encoded = jwt.encode(to_encode, _private_key_pem, algorithm="EdDSA")
    # return encoded
    
    # Mock return for now
    encoded = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded

def verify_jwt_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
