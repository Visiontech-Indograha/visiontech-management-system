"""Penjaga APP_ENV=production: API tidak boleh start dengan rahasia kosong / bawaan (dok 08)."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

_GOOD = {
    "APP_ENV": "production",
    "JWT_PRIVATE_KEY_HEX": "11" * 32,
    "DOC_SIGNING_KEY_HEX": "22" * 32,
    "MINIO_ACCESS_KEY": "vms-app",
    "MINIO_SECRET_KEY": "bukan-bawaan-123",
}


def _settings(**over: str) -> Settings:
    return Settings(_env_file=None, **{**_GOOD, **over})  # type: ignore[arg-type]


def test_production_with_all_secrets_starts():
    assert _settings().APP_ENV == "production"


@pytest.mark.parametrize(("field", "value"), [
    ("JWT_PRIVATE_KEY_HEX", ""),
    ("DOC_SIGNING_KEY_HEX", ""),
    ("MINIO_ACCESS_KEY", "[REDACTED-MINIO-USER]"),
    ("MINIO_SECRET_KEY", "[REDACTED-MINIO-USER]"),
])
def test_production_refuses_missing_or_default_secret(field: str, value: str):
    with pytest.raises(ValidationError, match=field):
        _settings(**{field: value})


def test_development_keeps_local_defaults():
    s = Settings(_env_file=None, APP_ENV="development", JWT_PRIVATE_KEY_HEX="")  # type: ignore[call-arg]
    assert s.JWT_PRIVATE_KEY_HEX == ""
