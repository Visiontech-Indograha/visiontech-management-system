"""Penjaga: tidak ada `SELECT *` / `RETURNING *` di SQL mentah api/app/.

Kolom harus disebut eksplisit supaya penambahan kolom di DB tidak diam-diam ikut keluar lewat API
dan bentuk hasil query tetap terkontrol. `COUNT(*)` diizinkan.
"""
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
_COUNT = re.compile(r"COUNT\s*\(\s*\*\s*\)", re.IGNORECASE)
_WILDCARD = re.compile(r"\b(?:SELECT|RETURNING)\s+(?:[A-Za-z0-9_]+\.)?\*", re.IGNORECASE)


def _violations() -> list[str]:
    found: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _WILDCARD.search(_COUNT.sub("", line)):
                found.append(f"{path.relative_to(APP_DIR)}:{number}: {line.strip()}")
    return found


def test_app_dir_is_found() -> None:
    assert any(APP_DIR.rglob("*.py")), "api/app tidak ditemukan — penjaga ini tidak memeriksa apa pun"


def test_no_wildcards_in_sql() -> None:
    violations = _violations()
    assert not violations, "Ditemukan wildcard (*) di SQL — sebut kolomnya:\n" + "\n".join(violations)


def test_guard_detects_wildcards() -> None:
    """Pengaman penjaga: pola benar-benar menangkap yang dilarang dan membiarkan COUNT(*)."""
    for bad in ("SELECT * FROM x", "select a.* from x a", "INSERT ... RETURNING *", "RETURNING wp.*"):
        assert _WILDCARD.search(_COUNT.sub("", bad)), bad
    assert not _WILDCARD.search(_COUNT.sub("", "SELECT COUNT(*) FROM x"))
