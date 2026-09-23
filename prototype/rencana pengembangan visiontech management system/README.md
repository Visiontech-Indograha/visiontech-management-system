# Rencana Pengembangan Visiontech Management System

Disusun 23 September 2026 · **Rencana terkunci** · Belum ada satu pun langkah setup dijalankan

Folder ini berisi rencana lengkap untuk membangun VMS menjadi aplikasi produksi.
Isinya **dokumen perencanaan saja** — tidak ada kode, tidak ada instalasi, tidak ada server
yang dinyalakan.

> **Baca [MULAI-DI-SINI.md](MULAI-DI-SINI.md) lebih dulu.** Dokumen itu ditulis khusus agar
> sesi baru di folder baru — manusia maupun agen AI — bisa langsung bekerja tanpa konteks
> percakapan sebelumnya.

---

## Daftar dokumen

| # | Berkas | Isi |
|---|---|---|
| — | **[MULAI-DI-SINI](MULAI-DI-SINI.md)** | **Pembuka. Tujuan, prinsip, bahan yang disalin, langkah pertama** |
| 00 | [Ringkasan Eksekutif](00-RINGKASAN-EKSEKUTIF.md) | Apa yang dibangun, berapa lama, berapa biaya, risiko |
| 01 | [Inventaris Aset](01-INVENTARIS-ASET.md) | Yang sudah ada di komputer ini + vonis pakai-ulang |
| 02 | [Keputusan Arsitektur](02-KEPUTUSAN-ARSITEKTUR.md) | 23 keputusan (ADR) beserta alasannya |
| 03 | [Cakupan Produk](03-CAKUPAN-PRODUK.md) | Modul, peran, aturan bisnis, MVP vs lanjutan |
| 04 | [Arsitektur Sistem](04-ARSITEKTUR-SISTEM.md) | Komponen, jaringan (Tailscale), alur data |
| 05 | [Kontrak API](05-KONTRAK-API.md) | Endpoint, konvensi, format galat, autentikasi |
| 06 | [Rencana Fase](06-RENCANA-FASE.md) | **Antrean kerja** per fase + Definition of Done |
| 07 | [Rencana Pengujian](07-RENCANA-PENGUJIAN.md) | Strategi uji, 12 regresi wajib, UAT |
| 08 | [Keamanan & Kepatuhan](08-KEAMANAN-DAN-KEPATUHAN.md) | Model ancaman, UU PDP, biometrik, kunci |
| 09 | [Operasional & Rilis](09-OPERASIONAL-DAN-RILIS.md) | Server, Tailscale, deploy, cadangan, runbook |
| 10 | [Keputusan Terkunci & Risiko](10-KEPUTUSAN-TERKUNCI-DAN-RISIKO.md) | **25 keputusan terkunci**, kebutuhan, 18 risiko |
| 11 | [Standar Frontend](11-STANDAR-FRONTEND.md) | Mobile-first, shadcn, atomic design, Zustand, DRY |
| 12 | [Standar Backend](12-STANDAR-BACKEND.md) | Struktur berlapis, SQLModel + asyncpg, aturan kode |
| 13 | [Berkas & Kompresi](13-PENGELOLAAN-BERKAS-DAN-KOMPRESI.md) | MinIO, kompresi foto, penyimpanan dokumen, retensi |
| 14 | [Daftar Pustaka](14-DAFTAR-PUSTAKA-TEKNOLOGI.md) | Seluruh pustaka + aturan menambah yang baru |
| 15 | [Templat CLAUDE.md](15-TEMPLATE-CLAUDE-MD.md) | Disalin ke akar repositori baru |
| 16 | [Glosarium](16-GLOSARIUM.md) | Istilah bisnis dan teknis |
| 17 | [CI/CD & Notifikasi](17-CI-CD-DAN-NOTIFIKASI.md) | GitHub Actions + Discord |

---

## Yang sudah dikunci

| Bagian | Keputusan |
|---|---|
| **Backend** | Python 3.12 · FastAPI · SQLModel · asyncpg · Alembic · struktur berlapis |
| **Basis data** | PostgreSQL 18 · PostGIS · pgvector · RLS aktif |
| **Penyimpanan** | MinIO; kompresi **hanya untuk foto**, dokumen disimpan apa adanya |
| **Web** | React 19 · TypeScript · Vite · shadcn/ui · Tailwind · TanStack Query · Zustand |
| **Mobile** | Flutter · shadcn_ui · Riverpod · go_router · dio · drift |
| **Tampilan** | **Mobile-first**: ponsel → tablet → desktop, termasuk untuk web kantor |
| **Komponen** | Wajib dari pustaka; buat sendiri hanya bila tidak ada, lalu masuk pustaka bersama |
| **CI/CD** | GitHub Actions · notifikasi dan peringatan ke **Discord** |
| **Jaringan** | Tailscale untuk SSH, psql, MinIO, staging. Hanya 443 yang publik |
| **Cakupan** | Prototipe = **MVP**. Fitur lanjutan sudah didaftar, tidak menyela |

---

## Hubungan dengan berkas lain

- **Prototipe (`../index.html`, `../js/`)** — definisi produk yang sah. Aturan bisnis di
  `js/domain.js` sudah diuji dan disetujui; aplikasi sungguhan harus menirunya persis.
- **Skema basis data (`../db/01`–`../db/05`)** — fondasi data, lengkap termasuk tanda tangan
  QR, sesi JWT, dan pengenalan wajah. Belum pernah dieksekusi.
- **`../agent.md`** — catatan serah terima prototipe.

---

## Prinsip penyusunan

1. **Prototipe adalah kebenaran, bukan inspirasi.** Aturan bisnis yang sudah disetujui tidak
   ditafsir ulang.
2. **Yang sudah ada dipakai ulang bila layak**, dibuang bila memperlambat — alasannya ditulis.
3. **Tidak menebak.** Angka dan temuan di sini berasal dari pemindaian nyata berkas dan mesin.
4. **Semuanya keputusan, bukan usulan.** Dokumen 10 adalah penguncinya; perubahan dicatat di
   Bagian D beserta tanggal dan dampaknya.
