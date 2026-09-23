---
name: Testing & Code Verification
description: Aturan pembuatan kode uji (test) oleh AI per fitur dan pemisahan pengujian lokal.
---

# Aturan Pengujian Kode (AI Testing Rules)

Sebagai AI pembangun VMS, Anda wajib menerapkan kebiasaan pengujian (testing) berikut pada setiap fitur:

1. **Uji Coba Bersamaan (TDD/Paired Testing)**:
   Setiap kali Anda menulis logika fitur (baik endpoint, service, maupun UI), Anda WAJIB membuat atau menjalankan skrip pengujian untuk memverifikasi bahwa kode tersebut benar-benar berfungsi sebelum menyatakan tugas selesai.

2. **Pemisahan Test Sementara (Lokal) vs Test Resmi (CI/CD)**:
   - **Test Sementara / Playground AI**: Skrip kotor, file percobaan manual, atau skrip pemanggilan API yang AI buat hanya untuk memastikan kodenya jalan (bukan *unit test* standar proyek) **HARUS** diletakkan di dalam folder `.local_tests/` di root proyek. 
   - Direktori `.local_tests/` telah dimasukkan ke `.gitignore`, sehingga file-file uji coba AI ini akan tetap berada di komputer lokal secara berdampingan dengan pengembangan fitur, tetapi **TIDAK AKAN PERNAH** ter-commit apalagi ter-push ke GitHub.
   
3. **Pengecualian untuk Unit Test Resmi**:
   *Unit test* resmi proyek yang terstruktur (seperti `api/tests/test_*.py` dengan pytest atau test `vitest` di web) tetap harus di-commit secara wajar karena GitHub Actions (CI/CD pipeline) sangat membutuhkannya untuk memvalidasi *Pull Request* otomatis.

4. **Definisi "Selesai" — WAJIB (T-11, `docs/PLAN-PERBAIKAN-TEMUAN.md`)**:
   Pada 2026-09-23 ditemukan bahwa backend yang di-CHANGELOG-kan "Fase 1–7 selesai" tidak dapat
   menyimpan satu baris pun: kodenya tidak pernah dijalankan. Karena itu sebuah task **hanya boleh
   disebut selesai** bila semua butir di bawah terpenuhi. Setiap butir berasal dari kegagalan nyata.

   | # | Syarat | Mencegah terulangnya |
   |---|---|---|
   | a | Uji resmi **dijalankan** dan hijau; laporan ke Pengguna menyertakan hasilnya (mis. "199 passed"). Keberadaan berkas, entri CHANGELOG, atau "kodenya sudah ditulis" **bukan** bukti selesai | Endpoint Fase 2–7 yang tidak pernah jalan |
   | b | Uji API dijalankan dengan `api/.venv` (**Python 3.12**, sama dengan Docker) terhadap **PostgreSQL sungguhan**. Uji yang ter-*skip* dihitung **belum** diuji | Impor `date` hilang yang lolos di 3.14 (T-16) |
   | c | Setiap endpoint **tulis** punya uji integrasi *tulis → baca ulang lewat koneksi terpisah* (`tests/conftest.py::sync_query`) | Sesi tidak pernah commit (T-02) |
   | d | Endpoint baru otomatis masuk `tests/test_route_smoke.py` (401 tanpa token, tidak pernah 500). Rute publik baru wajib ditambahkan ke `PUBLIC_ROUTES` beserta alasannya — itu keputusan keamanan | Endpoint 500 yang tak terdeteksi (T-01, T-09) |
   | e | Kode dari sesi/agen lain dianggap **belum terverifikasi** sampai dicocokkan dengan `db/*.sql` dan dijalankan. Jangan menyambungkan servis/repository yang belum pernah diuji | `AuthService` yang tidak cocok skema (A-2) |
   | f | Perubahan skema **hanya** lewat migrasi Alembic, dan `db/*.sql` disamakan **dalam commit yang sama** + ujinya | `new_id()` di server ≠ repo (T-15, 0002) |
   | g | Data uji dibuat lewat **jalur nyata**; jangan menyetel langsung kolom yang ditentukan trigger/fungsi DB (status absensi, jarak, dll.) | Trigger wajah tertimpa geofence (T-15) |
   | h | Daftar yang hidup di dua tempat (peran, jalur API, token desain) wajib punya **uji kesetaraan** | Peran `ADMIN` vs `admin` (T-03), `/api/v1` (T-07) |
   | i | Garis dasar `api/ruff.toml` hanya boleh **menyusut**; daftar `api/mypy.ini` hanya boleh **bertambah**. Berkas baru wajib bersih | Utang lint tumbuh diam-diam |
   | j | Penjaga otomatis (uji inventaris, pemindai) wajib **gagal bila yang diperiksanya kosong** | Penjaga `/api/v1` yang memeriksa 0 rute (T-09) |
   | k | Temuan baru di tengah task dicatat sebagai task baru di plan dan dikerjakan dalam **commit terpisah** — tidak dicampur diam-diam | — |
   | l | Entri CHANGELOG menyebut **berkas uji** yang membuktikan perubahannya | — |

   Perintah pemeriksaan penuh sebelum menyatakan selesai (dari folder `api/`):
   ```bash
   PYTHONPATH=. .venv/Scripts/python -m pytest -q      # atau .venv/bin/python di Linux/macOS
   .venv/Scripts/ruff check app tests
   PYTHONPATH=. .venv/Scripts/python -m mypy
   ```
   dan dari folder `web/`: `npm run lint && npm run typecheck && npm test`.
