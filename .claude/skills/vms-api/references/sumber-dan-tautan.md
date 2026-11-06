# Sumber dan tautan (vms-api)

Semua tanggal akses: 2026-11-04. Bagian "diverifikasi" berarti dibuka dan dibaca langsung pada tanggal itu.

## Dokumen internal VMS
- `C:\Users\ageng\visiontect-vms\vms-next\docs\panduan\panduan-fullstack.txt` (teks PDF, 2524 baris; bagian 1-4, 8, 10-13, 15-19, 21-22 dibaca).
- `C:\Users\ageng\visiontect-vms\riset-best-practice\01-PDF-DAN-AUDIT-VMS.md` (audit F-01 sampai F-36; nomor baris sebagian besar merujuk `vms-master-local`, bukan worktree ini).
- `C:\Users\ageng\visiontect-vms\riset-best-practice\02-API-DB-MINIO.md`.
- `C:\Users\ageng\visiontect-vms\vms-next\docs\01-STANDAR-ENGINEERING.md`, `03-SKEMA-DATA.md`, `06-KEAMANAN-DAN-OPERASI.md` (diverifikasi).
- `C:\Users\ageng\visiontect-vms\vms-next\docs\adr\0001-keputusan-awal.md` (keputusan 1-15, kriteria A-E).
- `C:\Users\ageng\visiontect-vms\vms-next\docs\adr\0003-referensi-best-practice.md` (daftar referensi R1-R13, praktik diadopsi/ditolak).

## Dokumentasi resmi
- PostgreSQL 18, fungsi UUID (`uuidv7()`): https://www.postgresql.org/docs/18/functions-uuid.html (diverifikasi).
- PostgreSQL, Row Security Policies (ENABLE, FORCE, BYPASSRLS, USING, WITH CHECK): https://www.postgresql.org/docs/current/ddl-rowsecurity.html (diverifikasi).
- FastAPI, Concurrency and async/await (`def` vs `async def`, threadpool): https://fastapi.tiangolo.com/async/ (diverifikasi).
- SQLAlchemy 2.0 dan asyncio: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html (dirujuk dari riset 02; belum dibuka pada tanggal ini).
- Alembic, `autocommit_block()`: https://alembic.sqlalchemy.org/en/latest/api/runtime.html (diverifikasi).
- OWASP API Security Top 10 2023: https://api-security.owasp.org/editions/2023/en/0x11-t10/ (diverifikasi; `owasp.org` mengalihkan ke alamat ini).
- Stripe, Idempotent requests (praktik 200 untuk duplikat identik): https://docs.stripe.com/api/idempotent_requests (dirujuk dari riset 01 bagian 6; belum dibuka pada tanggal ini).

## Repo referensi
- pgroll (expand-contract, versioned schema, PostgreSQL 14+): https://github.com/xataio/pgroll (diverifikasi README). Diadopsi sebagai pola, tidak sebagai alat (ADR 0003, pertimbangan versi APK lama).
- Supabase RLS guide (`(select current_setting(...))` dan indeks kolom filter): https://github.com/supabase/supabase (riset 02; ADR 0003 R10).
- `fastapi/full-stack-fastapi-template` (MIT, 46.164 bintang, push 2026-11-03): https://github.com/fastapi/full-stack-fastapi-template (riset 02; tidak diadopsi: SQLModel dan Traefik, ADR 0003 D1-D2).
- `benavlabs/FastAPI-boilerplate` (MIT): https://github.com/benavlabs/FastAPI-boilerplate (riset 02).
- `zhanymkanov/fastapi-best-practices` (tanpa lisensi; hanya konsep): https://github.com/zhanymkanov/fastapi-best-practices (ADR 0003 R1).
- squawk (linter SQL untuk migrasi): https://github.com/sbdchd/squawk (ADR 0003 R8; direncanakan, belum dipasang).
- strong_migrations (daftar operasi berisiko, gem Ruby; hanya daftar aturan): https://github.com/ankane/strong_migrations (ADR 0003 R7).
- bulletproof-react (struktur fitur web): https://github.com/alan2207/bulletproof-react (ADR 0003 R4).

## Keputusan proyek yang dirujuk
- `CLAUDE.md` proyek (aturan SQL R-31, ListParams, validasi query, rilis SemVer, DB uji).
- `docs/06` bagian Otorisasi, Idempotensi, Observability, Rilis.
- ADR 0001 keputusan 1-15 (uv, CodeQL/Trivy, refresh di PostgreSQL, EdDSA, log, health, idempotensi PG, uang, RLS, enkripsi NIK, notifikasi, tes sejajar, ADR, di luar scope).
- ADR 0002 keputusan 2 (versi, deprecation RFC 8594 dan RFC 9745), keputusan 9 (batas laju).
