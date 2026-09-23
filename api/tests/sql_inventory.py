"""
Inventaris literal SQL di `app/` untuk pemeriksaan terhadap skema (V-01).
Potongan di dalam f-string tidak diperiksa (bentuk akhirnya baru ada saat runtime) tetapi dihitung.
"""
from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

SQL_START = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|WITH)\b", re.IGNORECASE)
PARAM = re.compile(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)")


@dataclass(frozen=True)
class SqlLiteral:
    path: str
    line: int
    sql: str

    @property
    def key(self) -> str:
        """Kunci stabil (tidak berubah bila baris bergeser): berkas + hash SQL ternormalisasi."""
        digest = hashlib.sha1(" ".join(self.sql.split()).encode()).hexdigest()[:10]
        return f"{self.path}#{digest}"

    def as_prepared(self) -> str:
        names: dict[str, int] = {}
        return PARAM.sub(lambda m: f"${names.setdefault(m.group(1), len(names) + 1)}", self.sql)


def collect(root: Path = Path("app")) -> tuple[list[SqlLiteral], int]:
    """(literal SQL statis, jumlah SQL dalam f-string yang dilewati)."""
    found: list[SqlLiteral] = []
    dynamic = 0
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        inside_fstring = {id(v) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr) for v in node.values}
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                text = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
                dynamic += bool(SQL_START.match(text))
            elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                  and id(node) not in inside_fstring and SQL_START.match(node.value)):
                found.append(SqlLiteral(path.as_posix(), node.lineno, node.value))
    return found, dynamic
