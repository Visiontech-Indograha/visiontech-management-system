"""
R-31 · Larangan kueri PostgreSQL dari pemilik (docs/12 §1a). Pemeriksaan statis atas SEMUA literal string di
`app/` (termasuk potongan f-string) dan migrasi Alembic:

- `SELECT *`, `alias.*`, `RETURNING *`  → sebut kolom yang dibutuhkan;
- `OFFSET`                             → keyset/cursor pagination;
- `LIKE/ILIKE '%…'` atau `'%' || :q`   → Full-Text Search / `pg_trgm`;
- `NOT IN (SELECT …)`                  → `NOT EXISTS`;
- `TIMESTAMP` tanpa zona               → `TIMESTAMPTZ`;
- `CREATE INDEX` tanpa `CONCURRENTLY`  → hanya di migrasi BARU (migrasi lama = baseline, tidak diubah).

`KNOWN` mencatat pelanggaran lama per berkas; jumlahnya hanya boleh MENYUSUT (uji merah bila bertambah, dan
merah bila sudah berkurang tetapi angkanya belum diturunkan).
"""
from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RULES: dict[str, re.Pattern[str]] = {
    "select-star": re.compile(r"\bselect\s+(distinct\s+)?\*|\b[a-z_][a-z0-9_]*\.\*(?=\s*(,|from\b|$))"
                              r"|\breturning\s+\*", re.IGNORECASE | re.MULTILINE),
    "offset": re.compile(r"\boffset\s+(:\w+|\d+|\$\d+)", re.IGNORECASE),
    "like-leading-wildcard": re.compile(r"\bi?like\s+('%|'%'\s*\|\||concat\s*\(\s*'%')", re.IGNORECASE),
    "not-in-subquery": re.compile(r"\bnot\s+in\s*\(\s*select\b", re.IGNORECASE),
    "timestamp-without-tz": re.compile(r"\btimestamp\b(?!tz)(?!\s+with\s+time\s+zone)(?!\s*\()", re.IGNORECASE),
}
SQL_HINT = re.compile(r"\b(select|insert|update|delete|returning|where|from)\b", re.IGNORECASE)

# "berkas | aturan" → jumlah pelanggaran lama (R-31, 2026-09-30); hanya boleh menyusut.
KNOWN: dict[str, int] = {
    "app/modules/attendance/repositories/attendance_session_repository.py | offset": 1,
    "app/modules/audit/repositories/audit_repository.py | offset": 1,
    "app/modules/employees/repositories/employee_repository.py | like-leading-wildcard": 1,
    "app/modules/employees/repositories/employee_repository.py | offset": 1,
}


def _strings(path: Path) -> tuple[list[str], int]:
    """(teks SQL: konstanta string + f-string digabung, jumlah pola `%{q}%` untuk LIKE di sisi Python)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    inside = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr) for v in n.values}
    out: list[str] = []
    wildcard = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            parts = [v.value if isinstance(v, ast.Constant) else " _ " for v in node.values]
            out.append("".join(str(x) for x in parts))
            if isinstance(node.values[0], ast.Constant) and str(node.values[0].value) == "%":
                wildcard += 1  # f"%{q}%" → LIKE dengan wildcard di depan
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in inside:
            out.append(node.value)
    return out, wildcard


def _count() -> Counter[str]:
    found: Counter[str] = Counter()
    for path in sorted((ROOT / "app").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        texts, wildcard = _strings(path)
        found[f"{rel} | like-leading-wildcard"] += wildcard
        for text in texts:
            if not (SQL_HINT.search(text) or RULES["offset"].search(text)):
                continue
            for rule, pattern in RULES.items():
                if rule == "timestamp-without-tz":
                    continue  # tipe kolom hanya relevan di DDL (migrasi)
                found[f"{rel} | {rule}"] += len(pattern.findall(text))
    return +found


def test_rules_detect_bad_sql() -> None:
    bad = {
        "select-star": ["SELECT * FROM vms.x", "SELECT a.*, b.id FROM a", "UPDATE x SET y = 1 RETURNING *"],
        "offset": ["SELECT id FROM x LIMIT :limit OFFSET :offset"],
        "like-leading-wildcard": ["WHERE name ILIKE '%' || :q || '%'", "WHERE name LIKE '%abc%'"],
        "not-in-subquery": ["WHERE id NOT IN (SELECT user_id FROM y)"],
        "timestamp-without-tz": ["created_at timestamp NOT NULL"],
    }
    for rule, samples in bad.items():
        for sample in samples:
            assert RULES[rule].search(sample), (rule, sample)
    good = ["SELECT id, name FROM x", "created_at timestamptz", "WHERE name LIKE :q || '%'",
            "WHERE NOT EXISTS (SELECT 1 FROM y)", "SELECT count(*) FROM x WHERE id = :id"]
    for sample in good:
        assert not any(p.search(sample) for p in RULES.values()), sample


def test_no_new_forbidden_sql() -> None:
    counts = _count()
    grew = {k: (KNOWN.get(k, 0), v) for k, v in sorted(counts.items()) if v > KNOWN.get(k, 0)}
    assert not grew, "Kueri melanggar docs/12 §1a (lama → sekarang):\n" + "\n".join(
        f"  {k}: {a} → {b}" for k, (a, b) in grew.items())


def test_known_only_shrinks() -> None:
    counts = _count()
    shrunk = {k: (v, counts.get(k, 0)) for k, v in sorted(KNOWN.items()) if counts.get(k, 0) < v}
    assert not shrunk, "Sudah berkurang — turunkan/hapus di KNOWN:\n" + "\n".join(
        f"  {k}: {a} → {b}" for k, (a, b) in shrunk.items())
