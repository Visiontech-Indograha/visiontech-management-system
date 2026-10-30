"""
Versi SemVer tunggal: berkas VERSION di root adalah satu-satunya sumber. API (api/VERSION, /version),
web (web/package.json) dan mobile (mobile/pubspec.yaml) harus sama. Perbaiki dengan
`bash scripts/versi.sh --tulis`. Aturan kenaikan: docs/RILIS.md.
"""
import json
import re
from pathlib import Path

from app.core.version import APP_VERSION, SEMVER

ROOT = Path(__file__).resolve().parents[3]
PERBAIKI = "perbaiki dengan: bash scripts/versi.sh --tulis"


def _baca(relatif: str) -> str:
    berkas = ROOT / relatif
    assert berkas.is_file(), f"Berkas {relatif} tidak ada ({PERBAIKI})"
    return berkas.read_text(encoding="utf-8").strip()


def _versi_mobile() -> tuple[str, str]:
    cocok = re.search(r"^version:\s*(\S+)\s*$", _baca("mobile/pubspec.yaml"), re.MULTILINE)
    assert cocok, "mobile/pubspec.yaml tidak punya baris 'version: X.Y.Z+BUILD'"
    nama, _, build = cocok.group(1).partition("+")
    return nama, build


def test_version_file_is_semver():
    versi = _baca("VERSION")
    assert SEMVER.fullmatch(versi), f"VERSION '{versi}' bukan SemVer X.Y.Z"


def test_api_reads_the_same_version():
    assert _baca("VERSION") == APP_VERSION, f"API membaca versi lain ({PERBAIKI})"
    assert _baca("api/VERSION") == _baca("VERSION"), f"api/VERSION tidak sama dengan VERSION ({PERBAIKI})"


def test_web_package_version_matches():
    paket = json.loads(_baca("web/package.json"))
    assert paket["version"] == _baca("VERSION"), f"web/package.json version tidak sama dengan VERSION ({PERBAIKI})"


def test_mobile_pubspec_version_matches_and_build_is_numeric():
    nama, build = _versi_mobile()
    assert nama == _baca("VERSION"), f"mobile/pubspec.yaml '{nama}' tidak sama dengan VERSION ({PERBAIKI})"
    assert build.isdigit(), f"build number mobile '{build}' harus angka (X.Y.Z+N)"
