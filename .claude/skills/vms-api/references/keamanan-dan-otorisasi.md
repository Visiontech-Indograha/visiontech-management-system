# Keamanan dan otorisasi (API VMS)

Sumber: PDF bagian 10 (baris 1362-1481), bagian 13.1 (baris 1692-1731), OWASP API Security Top 10 2023 (https://api-security.owasp.org/editions/2023/en/0x11-t10/, akses 2026-11-04). Target: `vms-next/docs/06`, ADR 0001 keputusan 3, 4, 5, 9, 10.

## 1. Autentikasi (kondisi nyata)

| Aspek | Kode sekarang (bukti) | Status |
|---|---|---|
| Hash sandi | Argon2 untuk hash baru (`security.py:46-48`); bcrypt hanya saat verifikasi seed (`security.py:51-54`) | Sesuai. Verifikasi dan hash masih sinkron di event loop (`auth_service.py:145,314,322`) |
| Algoritma JWT | EdDSA; `kid` dikenal; HS256 dan `alg: none` ditolak (`security.py:7`, `:30`) | Sesuai ADR 0001 keputusan 4 |
| Kunci JWT | `JWT_PRIVATE_KEY_HEX` dari env, atau dibuat acak bila kosong (`security.py:33-39`) | Perlu cek: pembuatan acak saat env kosong berbahaya di produksi. Target: kunci wajib dari rahasia terpasang |
| Umur access token | 15 menit (`auth_service.py:25`) | Sesuai (PDF 10.1: 5-15 menit) |
| Refresh token | Tabel `user_sessions`; rotasi dengan `FOR UPDATE OF s` (`auth_session_repository.py:175`) | Sesuai. Hash SHA-256 (target) dan indeks belum ada (`vms-db`) |
| Reuse detection | Ada (`auth_service.py` menurut riset 01 T11) | Verifikasi sebelum mengklaim lengkap |
| Lockout login | `LOCK_MINUTES = 15` (`auth_session_repository.py:30`) | Sesuai `docs/06` (5 kegagalan → kunci 15 menit) |
| Respons generik | Hash pengganti dipakai untuk akun tidak ada (`auth_service.py:85`) | Sesuai `docs/06` |
| Tiket file | EdDSA, TTL 5 menit, jendela 30 menit (`security.py:131-151`) | Sesuai; dipakai untuk `/files/{id}/url` |

Rekomendasi:
- Jalankan `verify_password` dan `hash_password` lewat `await asyncio.to_thread(...)`. Tetap pertahankan hash pengganti agar waktu respons seragam.
- Pastikan access token menyertakan `sid` dan setiap request memeriksa sesi aktif (`docs/06`). Pencabutan sesi harus langsung berlaku.

## 2. Otorisasi: RBAC, ABAC, dan cakupan

- **RBAC** (izin per peran): `require_permission` (`api/app/api/deps.py:176`), `require_any_permission` (`:193`). Peran Master V2: `SUPER_ADMIN`, `OPERATIONAL_MANAGER`, `PROJECT_MANAGER`, `TEAM_LEADER`, `ADMIN_HR_GA`, `FINANCE`, `EMPLOYEE` (`docs/06`).
- **ABAC** (relasi objek): `check_daily_access` (`access_service.py:74`) memeriksa akses per objek, `ensure_same_org` (`:153`) memeriksa organisasi. Ini menutup BOLA di jalur jadwal dan kebanyakan modul (riset 01 T11).
- **Kelemahan**: pemeriksaan cakupan diulang di tiap handler/service. Audit VMS lama mencatat 7 kebocoran lintas divisi karena pembatasan hanya di kode (ADR 0001 keputusan 9, alasan). Satu jalur baru tanpa filter cukup untuk membocorkan data.
- **Target** (ADR 0001 keputusan 9): satu fungsi cakupan SQL dan satu helper di service yang sama; RLS sebagai jaring terakhir (lihat `vms-db`). Aturan `docs/06`: "Respons 404 (bukan 403) untuk objek yang tidak boleh diketahui keberadaannya."
- **Aksi admin** pada akun Super Admin hanya oleh Super Admin (`docs/06`).
- **Pemeriksaan peran di kode**: hindari pemeriksaan string peran tersebar (`ALLOWED_REVIEW_ROLES` di `leave_service.py:31`). Pindahkan ke peta izin terpusat (Target: `shared/authz/policy.py`, dites).

### Checklist BOLA (OWASP API1)
- [ ] Setiap `{id}` di path diperiksa kepemilikan atau cakupan sebelum dibaca atau diubah.
- [ ] Listing selalu difilter cakupan di SQL, bukan difilter di Python setelah dimuat (`apply_list`).
- [ ] ID lintas divisi → 404.
- [ ] Ada tes matriks peran × endpoint × ID lintas divisi (lihat `pengujian-kontrak-dan-galat.md`).

## 3. OWASP API Security Top 10 (2023), dipetakan ke VMS

| ID | Risiko | Kondisi VMS | Tindakan |
|---|---|---|---|
| API1 | Broken Object Level Authorization | Cakupan ada di kode, tidak terpusat | Helper cakupan + tes lintas divisi + RLS |
| API2 | Broken Authentication | Argon2, EdDSA, rotasi, lockout ada | Lihat bagian 1 (to_thread, kunci wajib) |
| API3 | Broken Object Property Level Authorization | Schema respons per endpoint | Pastikan respons tidak memuat hash, embedding, token; NIK dimask |
| API4 | Unrestricted Resource Consumption | Tidak ada rate limit umum; unggahan 10 MB; daftar tanpa LIMIT | Rate limit (lihat bagian 4) dan batas daftar |
| API5 | Broken Function Level Authorization | Ada `require_permission`; tes V-09 | Pertahankan tes `test_route_guards.py` |
| API6 | Unrestricted Access to Sensitive Business Flows | Approve/serah terima tanpa lock | Kondisi status (lihat transaksi) |
| API7 | SSRF | Panggilan keluar (face-service, FCM target) | Allowlist host keluar; timeout |
| API8 | Security Misconfiguration | Static mount `/uploads` aktif; CORS `*` bila `origins` kosong (`main.py:41`); Dockerfile root | Hapus mount; CORS ketat; non-root |
| API9 | Improper Inventory Management | Peta rute tersimpan (`route_inventory.py`) | Pertahankan inventaris dan tes smoke |
| API10 | Unsafe Consumption of APIs | Panggilan face-service dan notifikasi | Validasi respons; timeout; jangan percaya data luar |

Catatan: `main.py:41` memakai `allow_origins=origins or ["*"]` dengan `allow_credentials=bool(origins)`. Jika `origins` kosong, CORS terbuka untuk semua asal tanpa kredensial. Pastikan konfigurasi produksi mengisi `origins`. (Perlu cek nilai di deploy.)

## 4. Rate limiting

- Kondisi: tidak ada limiter umum. Yang ada hanya lockout login dan kode 429 (`core/errors.py:140`). Riset 01 F-19.
- Target (`docs/06`, ADR 0002 keputusan 9): login 6 per menit per IP+email (email di-hash); endpoint terotentikasi 120 per menit per pengguna. Penyimpanan Redis, dengan fallback memori per proses bila Redis tidak menjawab.
- Algoritma: token bucket atau sliding window. Jika memakai ZSET Redis, gunakan anggota unik (`f"{now_ms}-{uuid4().hex}"`). Anggota `str(now_ms)` menimpa anggota pada milidetik yang sama, sehingga hitungan kurang (koreksi PDF 8.4, riset 01 bagian 6).
- Mulai dengan mode catat saja (log) sebelum menolak. Pekerja lapangan bisa berbagi IP NAT.

## 5. Kriptografi data sensitif

- NIK dan rekening: AES-256-GCM di aplikasi, awalan key id, nonce acak 96-bit per nilai, kunci dari rahasia terpasang (Target ADR 0001 keputusan 10). Belum ada di kode (riset 01 T12).
- Pencarian persis lewat blind index HMAC-SHA256 dengan kunci terpisah. Tidak ada pencarian awalan pada nilai terenkripsi.
- Tampilan default dimask 4 digit terakhir. Nilai penuh hanya HR dan Super Admin, dicatat di audit "lihat data sensitif".
- `hide_parameters=True` pada `create_async_engine` agar parameter SQL tidak masuk log (riset 02 A-7; belum ada di `session.py`).

## 6. Keamanan dan pengamanan di dalam kode

- **Parameterized query saja**. Gunakan `:nama` dengan `text()`; jangan f-string untuk nilai. Tes `test_sql_rules.py` memindai f-string dengan `%` di depan.
- **Validasi input**: Pydantic v2 dengan `Field(max_length=…, ge=…, le=…)`. Batas harus sama dengan web dan mobile.
- **Galat**: jangan bocorkan stack trace, SQL, atau nama tabel. Galat `{"code","message"}`.
- **Log**: tanpa email, nama, NIK, token, sandi, embedding wajah. `user_id` (UUID mentah) boleh di log internal (ADR 0001 keputusan 5).
- **Unggahan**: lihat `vms-storage-minio`.
- **Webhook** (bila nanti ada): verifikasi HMAC-SHA256 dengan `hmac.compare_digest` (PDF 21, baris 2461-2477). Belum ada webhook masuk di VMS (riset 01 T21).

## 7. Kontainer (Docker)

Kondisi nyata di `api/Dockerfile` (bukti):
- Satu tahap `FROM python:3.12-slim` (baris 1), tanpa `USER` (proses sebagai root).
- `COPY . .` (baris 27) dan tidak ada `api/.dockerignore`. Ini memasukkan `.env` dan `uploads/` ke image. Build context `./api` (`docker-compose.yml:5-6`).
- Tidak ada `HEALTHCHECK`.
- Target (PDF 13.1, baris 1700-1732): multi-stage, `uv sync --frozen`, user non-root UID 10001, tanpa dependensi dev, CMD exec-form.

Tindakan prioritas (riset 01 F-01, F-02):
1. Tambah `api/.dockerignore`: `.env*`, `uploads/`, `backups/`, `.venv/`, `__pycache__/`, `tests/`, `.git/`.
2. Konfigurasi runtime lewat `env_file:` atau Docker secret, bukan file di image.
3. Tambah user non-root. Pastikan path LibreOffice dan folder tulis dapat dipakai user itu. Uji pratinjau laporan di container.
4. Tambah `HEALTHCHECK` atau biarkan compose yang mengurus.
5. Jika image pernah dipush ke registry, anggap kunci JWT dan `DOC_SIGNING_KEY` bocor, lalu rotasi (rotasi JWT mengeluarkan semua sesi).

## 8. Checklist keamanan

- [ ] Endpoint baru punya izin dan cakupan; ID lintas divisi → 404.
- [ ] Tidak ada `/uploads` statis; akses file lewat `/files/{id}/url`.
- [ ] Respons tanpa hash, embedding, token, NIK mentah.
- [ ] Log tanpa PII.
- [ ] Argon2 dan builder berat tidak memblokir event loop.
- [ ] Panggilan keluar punya timeout dan allowlist.
- [ ] Input dibatasi di Pydantic dan di query (`max_length`, `ge`, `le`).
- [ ] Dockerfile non-root, `.dockerignore` ada (sebelum merilis).
- [ ] Usulan `security-review` dijalankan sebelum merge perubahan auth atau izin.
