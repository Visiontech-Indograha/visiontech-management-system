"""
Skrip OPERATOR (tidak berjalan otomatis): bersihkan berkas pribadi yatim di MinIO yang tertinggal.

  python scripts/bersihkan_berkas_yatim.py --cek     # hanya melapor jumlah (tidak mengubah apa pun)
  python scripts/bersihkan_berkas_yatim.py --hapus   # menghapus (idempoten, aman diulang)

Yatim = (A) baris file_object tanpa pengunggah (akunnya sudah dihapus permanen) yang tak dirujuk data mana pun,
beserta objek dan semua varian `_full|_view|_thumb.webp`; (B) objek berpola `{uuid}/{uuid}[_varian].ext` di
bucket yang tak punya baris file_object dan tak dirujuk kolom kunci mana pun. Berkas yang masih dirujuk
(kolom kunci atau FK ke file_object, mis. logo tim) tidak disentuh. Keluaran hanya jumlah, tanpa kunci/isi.
Jalankan dari folder api/ dengan env aplikasi (DATABASE_URL, MINIO_*) yang menunjuk lingkungan target.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.core import storage
from app.core.file_cleanup import VARIANT_RE, is_referenced, purge_keys
from app.database.session import AsyncSessionLocal

UUID_KEY = re.compile(r"^[0-9a-f]{8}-[0-9a-f-]{27}/[0-9a-f]{8}-[0-9a-f-]{27}(?:_(?:full|view|thumb))?\.[A-Za-z0-9]+$")

_FK_COLUMNS = text(
    """
    SELECT c.conrelid::regclass::text AS tbl, a.attname AS col
    FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
    WHERE c.contype = 'f' AND c.confrelid = 'file_object'::regclass AND array_length(c.conkey, 1) = 1
    """
)


def _base(key: str) -> str:
    return VARIANT_RE.sub("", key.rsplit(".", 1)[0])


async def _fk_referenced(db, file_id) -> bool:
    for ref in (await db.execute(_FK_COLUMNS)).all():
        if ref.tbl == "file_object":
            continue
        hit = await db.execute(
            text(f'SELECT 1 FROM {ref.tbl} WHERE "{ref.col}" = :i LIMIT 1'), {"i": file_id}
        )
        if hit.first() is not None:
            return True
    return False


async def kumpulkan() -> tuple[list[tuple[object, str]], list[str]]:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("SELECT id, storage_key FROM file_object WHERE uploaded_by IS NULL"))).all()
        a: list[tuple[object, str]] = []
        for fid, key in rows:
            if not await is_referenced(db, key) and not await _fk_referenced(db, fid):
                a.append((fid, key))
        known = {_base(str(k)) for (k,) in (await db.execute(text("SELECT storage_key FROM file_object"))).all()}
        b: list[str] = []
        for name in storage.list_object_keys():
            if UUID_KEY.match(name) and _base(name) not in known and not await is_referenced(db, name):
                b.append(name)
        return a, b


async def main(hapus: bool) -> int:
    a, b = await kumpulkan()
    print(f"Baris file_object yatim (tanpa pengunggah, tak dirujuk): {len(a)}")
    print(f"Objek bucket tanpa baris file_object dan tak dirujuk: {len(b)}")
    if not hapus:
        print("Mode --cek: tidak ada yang diubah.")
        return 0
    if a:
        async with AsyncSessionLocal() as db:
            await db.execute(text("DELETE FROM file_object WHERE id = ANY(:ids)"), {"ids": [f for f, _ in a]})
            await db.commit()  # DB dulu, baru objek
    done, failed = purge_keys([k for _, k in a] + b)
    print(f"Objek dihapus: {done}; gagal: {failed} (ulangi bila ada yang gagal).")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--cek", action="store_true", help="hanya laporkan jumlah")
    mode.add_argument("--hapus", action="store_true", help="hapus berkas yatim")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.hapus)))
