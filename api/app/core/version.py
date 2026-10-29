"""
Versi aplikasi (SemVer) — satu sumber: berkas VERSION di root repo.

Salinannya `api/VERSION` ikut dalam citra Docker (konteks build hanya folder api/). Keduanya disinkronkan
oleh `bash scripts/versi.sh --tulis` dan diperiksa `tests/architecture/test_versi.py`.
"""
import re
from pathlib import Path

SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
_BERKAS = Path(__file__).resolve().parents[2] / "VERSION"


def baca_versi(berkas: Path = _BERKAS) -> str:
    """Baca dan validasi versi; galat jelas bila berkas hilang atau bukan SemVer X.Y.Z."""
    if not berkas.is_file():
        raise RuntimeError(f"Berkas versi tidak ada: {berkas}")
    nilai = berkas.read_text(encoding="utf-8").strip()
    if not SEMVER.fullmatch(nilai):
        raise RuntimeError(f"Versi '{nilai}' di {berkas} bukan SemVer X.Y.Z")
    return nilai


APP_VERSION = baca_versi()
