# CHANGELOG

Semua perubahan penting pada proyek VMS dicatat di sini.  
Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.0.0/) · Versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

> **Aturan wajib bagi semua AI dan developer:** Setiap perubahan **harus** dicatat di file ini sebelum commit. Lihat `.agy/rules/changelog.md` untuk panduan lengkap.

---

## [Unreleased] — `development`

### ✨ Ditambahkan

#### Arsitektur Backend (Blok A — Refactor) — 2026-09-23
- `api/app/core/errors.py` — `AppError`, `NotFoundError`, `ConflictError`, `InvalidStateError`, `ForbiddenError` + handler terpusat (semua error → JSON `{ code, message }` Bahasa Indonesia, tidak ada stack trace yang bocor).
- `api/app/core/time.py` — `utcnow()` dan `jakarta_now()` sebagai sumber tunggal waktu server. `datetime.now()` tidak boleh dipakai di tempat lain.
- `api/app/core/pagination.py` — Cursor pagination standar: encode/decode cursor, parse sort parameter, `PageResult[T]` generic.
- `api/app/repositories/base_repo.py` — `BaseRepo` dengan helper `execute`, `fetchone`, `fetchall`, `scalar`.
- `api/app/repositories/user_repo.py` — Semua query auth: `get_user_by_email`, `issue_session`, `rotate_session`, `revoke_session`, `login_is_locked`.
- `api/app/repositories/plan_repo.py` — Semua query SK: CRUD, `update_status` dengan optimistic lock, `create_document_snapshot`, `get_snapshot` (dengan JOIN members + days).
- `api/app/repositories/attendance_repo.py` — Semua query absensi: `get_site`, `distance_to_site` (PostGIS), `create_checkin`, `update_checkout`, `list_attendance`.
- `api/app/services/auth_service.py` — `AuthService`: login (cek lockout + bcrypt), refresh (rotasi token), logout, get_me.
- `api/app/services/plan_service.py` — `PlanService`: semua transisi status SK (publish, accept, start, request_completion, approve_completion, cancel) dengan validasi status dan optimistic lock.
- `api/app/services/document_service.py` — `DocumentService`: kanonisasi JSON deterministik, SHA-256, `next_serial_number` via DB function, `register_document_snapshot`.
- `api/app/services/attendance_service.py` — `AttendanceService`: check-in (geofence server-side, GPS palsu, face mismatch → NEEDS_REVIEW, duplikat dicegah), check-out (deteksi pulang cepat).
- `api/app/services/pdf_service.py` — `PdfService`: render PDF SK + QR code base64 via WeasyPrint + Jinja2, render BAST.
- `api/app/main.py` — Daftarkan `AppError` exception handler ke FastAPI app factory.

#### Sistem Desain UI (`design`) — 2026-09-23
- Dokumen sistem desain lengkap `docs/18-SISTEM-DESAIN-UI.md` — warna, tipografi, spasi, radius, elevasi, komponen, ikon, animasi, dan daftar larangan.
- Token desain tunggal `docs/design/tokens.json` — sumber kebenaran untuk semua nilai visual (brand, neutral, status, font, spasi, radius, gerak).
- Tema web `docs/design/web/theme.css` — variabel CSS untuk shadcn/ui + Tailwind v4, palet bawaan Tailwind dinonaktifkan, mode gelap dikunci ke `.dark` yang tidak pernah dipasang.
- Tema Flutter `mobile/lib/core/theme/` — `VmsColors`, `VmsTextStyles`, `VmsSizes`, `VmsTheme.light` (Material 3 penuh: AppBar, Card, Button, Input, BottomNav, Dialog, SnackBar, Switch, Tab, Badge, BottomSheet).
- Aturan AI desain `·agy/rules/design-system.md` — mengikat semua AI yang mengerjakan komponen UI.

#### Absensi Lapangan — Backend (Fase 4) — 2026-09-23
- `POST /sites` · `GET /sites` · `DELETE /sites/{id}` — CRUD master lokasi proyek dengan radius geofence (PostGIS).
- `POST /attendance/check-in` — validasi jarak (`ST_Distance`), deteksi terlambat, penanda GPS/Simulasi, swafoto, face result fallback → `NEEDS_REVIEW`.
- `POST /attendance/check-out` — deteksi pulang cepat, update status.
- `POST /attendance/{id}/explain` — penjelasan karyawan untuk absensi bermasalah.
- `POST /attendance/{id}/review` — tinjauan Finance/HR, mengubah status menjadi `APPROVED` atau `REJECTED`.
- `GET /attendance/export` — ekspor CSV (tanggal, NIK, nama, lokasi, jam masuk/keluar, status).
- `POST /cron/attendance/alert-missing` — peringatan Discord bila karyawan belum check-in pukul 09.00.
- `POST /cron/attendance/alert-needs-review` — peringatan Discord bila jumlah `NEEDS_REVIEW` melonjak (>10).

#### Pengenalan Wajah — Backend (Fase 8, parsial) — 2026-09-23
- Payload `check-in` menerima `face_result` dan `face_similarity` dari klien Mobile.
- `NO_MATCH` atau `LOW_QUALITY` secara otomatis menjadikan absensi `NEEDS_REVIEW` — karyawan tidak ditolak, Finance/HR yang memvalidasi.

#### HSE & Laporan Harian — Backend (Fase 5, mekanisme) — 2026-09-23
- `POST /hse/incidents` — laporan insiden K3 dengan bukti file.
- `POST /hse/incidents/{id}/resolve` — penyelesaian insiden.
- `POST /hse/daily-reports/{day_id}` — upsert laporan harian (body, kendala, bukti).
- `POST /hse/daily-reports/{day_id}/submit` — pengajuan laporan (validasi panjang minimum 10 karakter via DB check constraint).

#### Aset & BAST — Backend (Fase 7, mekanisme) — 2026-09-23
- `GET /assets` · `POST /assets` — daftar dan tambah aset (kendaraan/alat).
- `POST /assets/allocate` — alokasi aset ke SK dengan cek ketersediaan dan validasi SIM pengemudi.
- `POST /assets/allocations/{id}/return` — pengajuan formulir BAST pengembalian aset.
- `POST /assets/returns/{id}/verify` — verifikasi BAST oleh OPS, mencabut alokasi dan mengembalikan status aset ke `AVAILABLE`.

#### SK & Transisi Pekerjaan — Backend (Fase 3) — 2026-09-23
- `POST /plans` · `GET /plans` · `GET /plans/{id}` · `PUT /plans/{id}` — CRUD draft SK dengan optimistic locking (`row_version`).
- `POST /plans/{id}/days` · `POST /plans/{id}/days/{day_id}/tasks` — tambah hari kerja dan tugas ke SK.
- `POST /plans/{id}/publish` — penerbitan SK: mengubah status, membuat nomor SK, membuat snapshot JSONB + SHA-256 di `plan_document`.
- `POST /plans/{id}/accept` — penerimaan SK oleh ketua tim; menetapkan tanggal mulai.
- `POST /plans/{id}/start` · `POST /plans/{id}/complete` · `POST /plans/{id}/cancel` — transisi status lanjutan.
- `POST /plans/{plan_id}/changes/extension` — usulan adendum perpanjangan waktu SK.
- `POST /plans/{plan_id}/changes/{change_id}/approve` — persetujuan adendum; memperpanjang `period` dan `valid_period` anggota secara atomik.
- `GET /employees/{id}/conflicts?start_date=&end_date=` — cek bentrok jadwal personel via `vms.personnel_conflict()`.

#### Karyawan & Dokumen — Backend (Fase 2) — 2026-09-23
- `POST /employees` · `GET /employees` · `GET /employees/{id}` · `PATCH /employees/{id}` — manajemen karyawan.
- `POST /employees/{id}/offboard` — offboard karyawan + nonaktifkan akun login.
- `POST /employees/{id}/assignments` · `GET /employees/{id}/assignments` — riwayat penugasan/jabatan berbasis waktu.
- `POST /documents` · `GET /documents` · `GET /documents/{id}` — CRUD dokumen karyawan (SIM, sertifikat K3, kontrak).
- `POST /documents/{id}/verify` · `POST /documents/{id}/reject` — verifikasi dokumen oleh HR.
- `GET /expiry/documents` — daftar dokumen yang sudah/hampir kadaluarsa via `vms.v_document_expiry`.
- `POST /cron/expiry/run` — cron job otomatis mengubah status dokumen kadaluarsa.

#### Storage & File — Backend (Fase 2) — 2026-09-23
- `POST /files/upload` — upload file dengan validasi magic bytes, batas 10 MB, deduplication SHA-256.
- Kompresi gambar asinkron ke 3 varian WebP: `thumb` (200px), `view` (800px), `full` (1920px) via Pillow.
- Abstraksi MinIO `app/core/storage.py`.

#### Autentikasi & Sesi — Backend (Fase 1) — 2026-09-23
- `POST /auth/login` — login via DB function `vms.issue_session`, cek lockout `vms.login_is_locked`.
- `POST /auth/refresh` — rotasi refresh token via `vms.rotate_session`; token lama tidak dapat dipakai ulang.
- `POST /auth/logout` — pencabutan sesi aktif.
- `GET /auth/me` — profil user + daftar permissions.
- `GET /audit/events` — log audit terfilter per organisasi.
- CLI `create-admin`, `seed`, `cleanup-orphans` via `app/cli.py`.
- Discord security alerts via `app/core/alerts.py` (RLS injection failure, session reuse).
- RBAC permissions mapping per peran di `app/core/permissions.py`.

### 🔧 Diperbaiki

- **`attendance_cron.py`**: Import `send_security_alert` yang tidak ada diganti dengan `send_discord_alert` yang benar — mencegah `ImportError` saat aplikasi dimulai.
- **`plan_transitions.py`**: `issued_by` di tabel `plan_document` sekarang diisi `employee_id` (bukan `user_id`) sesuai FK constraint skema database.
- **`auth.py`**: User yang tidak aktif (`is_active = false`) tidak dapat memperbarui token meskipun refresh token masih valid.
- **`deps.py`**: Tambah try/except + Discord alert di sekitar `SET LOCAL` RLS injection; gagal tidak lagi memberikan akses tanpa konteks.
- **`core/errors.py`** (2026-09-23): Respons `AppError` kini memakai bentuk baku dokumen 05 §2 — `{"error": {"code", "message", "details"}}` — sama dengan handler lain dan yang dibaca `web/src/lib/api.ts`. Sebelumnya `{code, message}` di tingkat atas sehingga web tidak bisa membaca pesan galat. `AppError` mendapat parameter `details`; `status` menjadi keyword-only. Uji: `api/tests/test_errors.py`.

### 🏗️ Infrastruktur & Aturan AI

- `.agy/rules/git-flow.md` — aturan Git Flow ketat untuk AI dan developer.
- `.agy/rules/ai-testing.md` — aturan isolasi test lokal di `.local_tests/` agar tidak ikut ke GitHub.
- `.agy/rules/tailwind-v4.md` — aturan penggunaan Tailwind CSS v4 (tidak boleh konfigurasi v3).
- `.agy/rules/design-system.md` — aturan sistem desain mengikat untuk web dan mobile.
- `.agy/rules/changelog.md` — aturan ini (wajib menulis CHANGELOG sebelum commit).

---

## [0.0.1] — 2026-09-23 — Fase 0: Fondasi

### ✨ Ditambahkan
- Struktur monorepo `vms/`: `api/`, `web/`, `mobile/`, `db/`, `docs/`, `face-service/`.
- Skema database PostgreSQL 16 + PostGIS: 35+ tabel, RLS, partisi bulanan (attendance, audit_event, qr_scan).
- `db/04_signature_auth.sql` — tanda tangan digital QR + sesi JWT (EdDSA, refresh token as hash, family revocation).
- `db/05_face.sql` — pengenalan wajah pgvector 512-d, biometric consent, purge embedding.
- Scaffold FastAPI + Alembic baseline.
- Scaffold React 19 + Vite + Tailwind v4 + shadcn/ui + TanStack Query + Zustand.
- Scaffold Flutter + flutter_riverpod + go_router + drift (SQLite luring) + shadcn_ui.
- CI/CD GitHub Actions (echo placeholder, belum diisi penuh).
- Docker Compose: PostGIS 16, MinIO, Redis, face-service.
- Sanitisasi Discord alert (sensor NIK, email, token, telepon).

---

*File ini diperbarui terakhir: 2026-09-23 oleh Antigravity (Claude Sonnet 4.6)*
