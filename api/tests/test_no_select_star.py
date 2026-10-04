import os
import re
from pathlib import Path


def test_no_wildcards_in_sql():
    """Memastikan tidak ada kueri SQL di dalam api/app/ yang menggunakan SELECT * atau RETURNING *.
    COUNT(*) diizinkan.
    """
    app_dir = Path(__file__).parent.parent / "app"
    assert app_dir.exists(), "Direktori app/ tidak ditemukan"

    violations = []
    
    # Regex menangkap:
    # 1. SELECT *
    # 2. SELECT alias.* (misal a.*, wp.*)
    # 3. RETURNING *
    # 4. RETURNING alias.*
    # Mengecualikan COUNT(*)
    pattern = re.compile(
        r'(?i)\b(SELECT|RETURNING)\s+(?:[a-zA-Z0-9_]+\.)?\*(?!\s*\))'
    )

    for root, _, files in os.walk(app_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            
            filepath = Path(root) / file
            content = filepath.read_text(encoding="utf-8")
            
            for i, line in enumerate(content.splitlines(), 1):
                # Abaikan baris yang secara eksplisit merupakan COUNT(*)
                # (Meski regex sudah berusaha, terkadang pemformatan spasi bisa lolos)
                if "COUNT(*)" in line.replace(" ", "").upper():
                    # Jika satu-satunya wildcard di baris ini adalah COUNT(*), aman.
                    # Hapus dulu COUNT(*) dari teks untuk ngecek wildcard lain.
                    cleaned = re.sub(r'(?i)COUNT\s*\(\s*\*\s*\)', '', line)
                    if pattern.search(cleaned):
                        violations.append(f"{filepath.relative_to(app_dir)}:{i}: {line.strip()}")
                elif pattern.search(line):
                    violations.append(f"{filepath.relative_to(app_dir)}:{i}: {line.strip()}")

    assert not violations, "Ditemukan wildcard (*) dalam kueri SQL:\n" + "\n".join(violations)
