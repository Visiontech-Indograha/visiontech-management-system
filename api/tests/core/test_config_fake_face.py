"""Penjaga mode wajah palsu (FACE_FAKE_MODE): hanya boleh aktif di APP_ENV=development, selain itu API gagal start."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**over: object) -> Settings:
    return Settings(_env_file=None, **over)  # type: ignore[arg-type]


def test_fake_mode_is_off_by_default():
    assert _settings(APP_ENV="development").FACE_FAKE_MODE is False


def test_fake_mode_allowed_in_development():
    assert _settings(APP_ENV="development", FACE_FAKE_MODE=True).FACE_FAKE_MODE is True


@pytest.mark.parametrize("env", ["production", "test", "staging"])
def test_fake_mode_refuses_to_start_outside_development(env: str):
    with pytest.raises(ValidationError, match="FACE_FAKE_MODE"):
        _settings(APP_ENV=env, FACE_FAKE_MODE=True)


def test_default_requires_face_enrollment():
    """F8: bawaan kode tetap mewajibkan pendaftaran wajah (absen tanpa wajah ditolak / ditandai)."""
    assert _settings(APP_ENV="production", JWT_PRIVATE_KEY_HEX="11" * 32, DOC_SIGNING_KEY_HEX="22" * 32,
                     MINIO_ACCESS_KEY="vms-app", MINIO_SECRET_KEY="bukan-bawaan-123").FACE_ENROLLMENT_REQUIRED is True
