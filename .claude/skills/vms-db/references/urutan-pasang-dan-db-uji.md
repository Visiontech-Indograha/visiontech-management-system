# Urutan pasang skema, DB uji, backup (vms-db)

Sumber: `db/README.md` (baris 8-12), `.github/workflows/ci.yml` (baris 31, 56-75), `api/tests/db_guard.py`, `api/tests/conftest.py`, `deploy/` (skrip backup), `docs/06` (Cadangan dan Rilis), riset 01 F-30 dan T22, memori `vms-master-local-test-db`.

## 1. Urutan pasang

| Langkah | Berkas | Isi |
|---|---|---|
| 1 | `db/06_master_schema_v2.sql` | Skema dasar: tabel, enum/check, indeks, partisi log, soft delete |
| 2 | `db/08_master_v2_tambahan.sql` | Tambahan: `client`, `job_position`, `leave_balance`, `leave_request`, `operational_expense`, `project` (`08:14`, `:26`, `:39`, `:49`, `:69`, `:89`). Idempoten |
| 3 | `alembic upgrade head` (`api/alembic_v2`) | Migrasi lanjutan `v2_0001` … `v2_0019` |
| 4 | Aplikasi start | `prepare_v2_runtime` membuat partisi log (DDL runtime, akan dipindah) |
| - | `db/07_master_seed_v2.sql` | Data uji. **Hanya dev dan uji**, jangan di produksi (`db/README.md:9`) |

Catatan: `db/README.md:12` menulis "Urutan pasang: `06` → `08` → `alembic_v2 upgrade head`. `07` opsional untuk data uji."

Di CI (`ci.yml:62-75`): loop `06` lalu `08` dengan `psql -v ON_ERROR_STOP=1`, lalu `python -m alembic upgrade head`.

## 2. Bug urutan `client` (kejadian nyata)

- Gejala: CI gagal memasang skema.
- Sebab: `06` (baris 799 dan 817) mereferensikan `client(client_id)` sebelum `08` membuat `client` (`08:14`). `ON_ERROR_STOP=1` menghentikan proses.
- Perbaikan: pindahkan `client_sites` sampai `work_order_bom` ke `08`, setelah `client` dibuat. Commit `d8a12df5` (cabang `integrasi/uji-ulang`, judul: "pindahkan tabel client_sites..work_order_bom ke 08 agar dibuat setelah tabel client (CI gagal pasang skema)").
- Status di `origin/beta` (HEAD `d1a3d4e5`): **belum diperbaiki**. `git merge-base --is-ancestor d8a12df5 HEAD` gagal.
- Pelajaran: (a) tabel dengan FK harus dibuat setelah rujukannya; (b) CI harus gagal lebih awal bila urutan salah; (c) setiap perubahan `06` atau `08` diuji dengan pemasangan dari kosong, bukan hanya dengan migrasi.
- Post-mortem (blameless, PDF 22.2, baris 2510-2521): tulis timeline UTC, 5 Whys, dan action items bila belum dicatat (riset 01 T28).

## 3. Verifikasi pemasangan dari kosong

Langkah yang diusulkan (jalankan di DB uji saja, atas perintah user):
```bash
createdb vms_test   # atau reset DB uji lokal
psql -h localhost -U <superuser> -d vms_test -v ON_ERROR_STOP=1 -q -f db/06_master_schema_v2.sql
psql -h localhost -U <superuser> -d vms_test -v ON_ERROR_STOP=1 -q -f db/08_master_v2_tambahan.sql
cd api && alembic upgrade head
```
Jangan jalankan perintah ini dengan `DATABASE_URL` yang menunjuk ke `vms-dev-db` atau produksi.

## 4. DB uji

### 4.1 Aturan
- Tes memakai `TEST_DATABASE_URL` (`db_guard.py:38-51`). `conftest.py:36` menolak URL yang bukan lokal dan tidak berakhiran `_test` atau berawalan `test_`.
- Nama yang diizinkan: `*_test`, `test_*`, atau daftar `TEST_ALLOW_DB_NAMES` (`db_guard.py:21-22`).
- Host lokal: `localhost`, `127.0.0.1`, `::1`, `db`, `postgres` (`db_guard.py:10`). Host `db` atau `postgres` diizinkan karena nama layanan compose atau CI. Pastikan nama DB tetap `*_test`.
- DB uji lokal per memori: `vms-master-local` memakai `test_migration` (V2 murni, tanpa skema `vms`). Fitur V1 ditulis ulang ke V2.
- Port DB dev (`vms-dev-db` :55433) dan DB uji (`vms-test-db` :55432) dari `CLAUDE.md` proyek. Setelah Docker restart: `docker start vms-test-db`. Tes DB dilewati bila DB mati (`CLAUDE.md`).
- Data uji buatan sendiri dihapus setelah dipakai (`CLAUDE.md` Aturan, akun uji di `scripts/akun-uji-lokal.txt`).

### 4.2 Celah
- `ci.yml:31`: CI memakai `postgres:postgres@.../visiontech_db`. Nama `visiontech_db` tidak berakhiran `_test`, tetapi host `localhost` lolos sebagai lokal. Tes CI tetap berjalan karena host lokal. Pertimbangkan nama `visiontech_test` untuk CI agar aturan nama tidak bergantung pada host.
- Superuser di CI melewati RLS. Tes RLS wajib memakai peran non-superuser (`vms-db` bagian RLS).

## 5. Backup dan uji pulih

Kondisi (bukti):
- Skrip ada di `deploy/`: `backup.sh`, `backup-offsite.sh`, `siapkan-offsite.sh`, `uji-pulih-cadangan.sh`, `uptime-kuma.compose.yml`, `status-layanan.sh`, `healthcheck.sh`.
- Jadwal dan RPO/RTO tidak tertulis di kode (riset 01 F-30). Modul `api/app/modules/system_backup/` mencatat registry dan SHA-256 (`backup_service.py:44`).

Target (`docs/06` Cadangan):
- `pg_dump` harian ke MinIO dan salinan luar situs.
- Uji pulih berkala ke DB uji, bukan produksi.
- Akses DB dan MinIO hanya lewat Tailscale; tanpa port DB publik; SSH hanya kunci. Kondisi port: `deploy/tutup-port-db.sh` ada (periksa apakah sudah dijalankan).
- Tulis RPO dan RTO (PDF 17.2, baris 2003-2012). Contoh format: RPO 24 jam (cadangan harian), RTO 2 jam (target usulan, perlu keputusan pemilik).
- Sebelum rilis yang mengubah skema: `pg_dump` berlabel versi (`docs/06` Rilis langkah 3a).

Uji pulih (langkah umum, atas perintah user):
1. Ambil berkas cadangan terbaru.
2. Restore ke `vms_test` (bukan produksi).
3. Jalankan `alembic current` dan bandingkan dengan head rilis.
4. Jalankan query hitung baris tabel inti dan bandingkan dengan sumber.
5. Catat waktu dan hasil di runbook.

## 6. Checklist

- [ ] Urutan 06 → 08 → alembic dijaga; tabel dengan FK dibuat setelah rujukannya.
- [ ] Pemasangan dari kosong diuji di `vms_test`.
- [ ] Tes hanya di DB `*_test` atau lokal; tidak ada DB dev atau produksi.
- [ ] `db/07` (seed) tidak pernah dijalankan di produksi.
- [ ] Pertanyaan CI: nama DB uji dan peran superuser sudah dibahas.
- [ ] RPO, RTO, dan jadwal backup tertulis; uji pulih tercatat.
- [ ] Backup sebelum rilis skema.
