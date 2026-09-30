"""
O-02 (docs/20 §5, R-25) · Router tidak pernah menyentuh basis data (CLAUDE.md, docs/12 §2).
Router hanya: jalur, metode, status, model respons, dependency; SQL tinggal di crud.

Pemeriksaan statis (AST) atas `app/api/v1/endpoints/*.py`: router tidak boleh mengimpor pembangun kueri
SQLAlchemy (`text`, `select`, `insert`, `update`, `delete`) dan tidak boleh memanggil metode sesi
(`db.execute`, `db.scalar`, …). `LEGACY` hanya boleh MENYUSUT: router baru yang melanggar langsung
merah, dan router di daftar yang sudah bersih juga merah (hapus barisnya).
"""
from __future__ import annotations

import ast
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints"

# Bukan router: dependency sesi yang MEMANG menyetel konteks transaksi (`set_config`, dok 12 §3).
NOT_ROUTERS = {"deps.py"}

QUERY_BUILDERS = {"text", "select", "insert", "update", "delete"}
SESSION_CALLS = {"execute", "scalar", "scalars", "get", "add", "flush", "commit", "refresh", "merge"}

# berkas → alasan masih ada; hanya boleh menyusut (dikosongkan oleh R-25b per modul).
LEGACY: dict[str, str] = {
    "assets.py": "R-25b",
    "attendance.py": "R-25b",
    "audit.py": "R-25b",
    "employees.py": "R-25b",
    "expiry.py": "R-25b",
    "files.py": "R-25b",
    "hse.py": "R-25b",
    "work_plans.py": "R-25b",
    "sites.py": "R-25b",
}


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sqlalchemy"):
            names = {a.name for a in node.names} & QUERY_BUILDERS
            found += [f"{path.name}:{node.lineno} impor sqlalchemy.{n}" for n in sorted(names)]
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in SESSION_CALLS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "db"
        ):
            found.append(f"{path.name}:{node.lineno} db.{node.func.attr}()")
    return found


def _all() -> dict[str, list[str]]:
    return {
        p.name: v
        for p in sorted(API_DIR.glob("*.py"))
        if p.name not in NOT_ROUTERS and (v := _violations(p))
    }


def test_scanner_detects_a_router_that_queries(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(
        "from sqlalchemy import text\n"
        "async def f(db):\n"
        "    await db.execute(text('SELECT 1'))\n",
        encoding="utf-8",
    )
    assert _violations(bad) == ["bad.py:1 impor sqlalchemy.text", "bad.py:3 db.execute()"]


def test_no_new_router_touches_the_database() -> None:
    new = {name: v for name, v in _all().items() if name not in LEGACY}
    assert not new, "Router menyentuh DB — pindahkan kueri ke crud:\n" + "\n".join(
        f"  {line}" for v in new.values() for line in v
    )


def test_legacy_list_only_shrinks() -> None:
    clean = sorted(name for name in LEGACY if name not in _all())
    assert not clean, f"Router sudah bersih — hapus dari LEGACY: {clean}"
