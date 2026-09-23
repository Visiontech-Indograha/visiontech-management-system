# 15 · Templat `CLAUDE.md`

Salin seluruh isi blok di bawah menjadi **`vms/CLAUDE.md`** di akar repositori baru.
Berkas ini dibaca otomatis oleh agen di setiap sesi, jadi aturannya tidak perlu diulang
setiap kali.

Beri nama `AGENTS.md` bila Anda memakai agen lain yang membaca berkas itu; isinya sama.

---

```markdown
# VMS — Visiontech Management System

Aplikasi manajemen pekerjaan lapangan PT Visiontech: SK penugasan, absensi lapangan,
laporan, aset, insiden K3, lembur, dokumen kepegawaian, tanda tangan digital ber-QR.

**Baca `docs/MULAI-DI-SINI.md` lebih dulu.** Antrean kerja ada di `docs/06-RENCANA-FASE.md`.

## Tiga aturan produk yang tidak boleh dilanggar

1. **Kewenangan mengikuti SK, bukan jabatan.** Ketua sebuah pekerjaan ditentukan surat
   keputusan yang berlaku. Ganti ketua lewat adendum → kewenangan berpindah hari itu juga;
   ketua lama kehilangan hak ketua tetapi tetap punya hak anggota bila masih terdaftar.
2. **Dokumen terbit tidak pernah berubah.** Perubahan = versi baru. Versi lama terkunci.
3. **Jangan percaya perangkat.** Waktu dan jarak absensi dihitung ulang di server.

## Tumpukan teknologi (dikunci — jangan diganti)

- **Backend:** Python 3.12 · FastAPI · SQLModel · asyncpg · Alembic (async)
- **Basis data:** PostgreSQL 18 · PostGIS · pgvector · RLS aktif
- **Penyimpanan:** MinIO; kompresi **hanya foto**, dokumen disimpan apa adanya
- **Web:** React 19 · TypeScript strict · Vite · shadcn/ui · Tailwind · TanStack Query · Zustand
- **Mobile:** Flutter · shadcn_ui · Riverpod · go_router · dio · drift
- **Auth:** JWT EdDSA pendek + refresh berotasi · argon2id
- **PDF:** Jinja2 + WeasyPrint di server
- **CI/CD:** GitHub Actions → notifikasi Discord (`#vms-ci`, `#vms-deploy`, `#vms-alerts`)
- **Jaringan:** Tailscale untuk SSH/psql/MinIO/staging; hanya 443 publik

Daftar pustaka lengkap dan aturan menambah pustaka: `docs/14-DAFTAR-PUSTAKA-TEKNOLOGI.md`.

## Struktur

```
api/            FastAPI — router → controller → service → repository
web/            React — components/{ui,molecules,organisms,templates} + features/
mobile/         Flutter — core/, shared/, features/
face-service/   layanan wajah (fase 8)
db/             5 berkas SQL, fondasi skema
prototype/      prototipe V2 — RUJUKAN, JANGAN DIUBAH
docs/           seluruh rencana dan standar
```

## Sebelum menulis kode

| Yang dikerjakan | Baca dulu |
|---|---|
| Endpoint / servis | `docs/12-STANDAR-BACKEND.md`, `docs/05-KONTRAK-API.md` |
| Komponen / halaman | `docs/11-STANDAR-FRONTEND.md` |
| Unggahan berkas | `docs/13-PENGELOLAAN-BERKAS-DAN-KOMPRESI.md` |
| Auth, izin, biometrik | `docs/08-KEAMANAN-DAN-KEPATUHAN.md` |
| CI, deploy, peringatan | `docs/17-CI-CD-DAN-NOTIFIKASI.md` |
| Aturan bisnis apa pun | `prototype/js/domain.js` — sumber kebenaran |

## Aturan backend

- Lapisan: **router → controller → service → repository**. Router tidak pernah menyentuh
  basis data. Service tidak pernah menulis SQL.
- Nama fungsi servis **sama** dengan transaksi di `prototype/js/domain.js`
  (`publish`, `accept`, `request_personnel_change`, …).
- **Jangan pernah mengembalikan model SQLModel sebagai respons API.** Selalu lewat skema.
- Satu permintaan = satu sesi = satu transaksi, dengan `SET LOCAL app.user_id` /
  `app.organization_id`. Sesi tidak pernah dibagikan ke `asyncio.gather`.
- Relasi dimuat eksplisit (`selectinload`) — lazy loading tidak bekerja di async.
- Kolom PostGIS tidak pernah keluar mentah; selalu diubah menjadi `{lat, lon}`.
- Kerja berat (kompresi gambar, render PDF) → `run_in_threadpool`.
- Waktu hanya lewat `core/time.py`. Rahasia hanya lewat `core/config.py`.
- Galat: `AppError(code, message)` dengan **message Bahasa Indonesia untuk pengguna**.
- Berkas yang tidak berwenang → **404**, bukan 403.

## Aturan frontend

- **Mobile-first.** Gaya dasar untuk ponsel, tambahkan dengan `md:` dan `lg:`. Tidak pernah
  `max-*`.
- **Wajib pakai shadcn/ui.** Tidak ada → susun dari yang ada → benar-benar tidak ada → buat
  sendiri dengan token yang sama, taruh di `components/`.
- Naikkan komponen ke pustaka bersama **setelah** dipakai dua kali, bukan sebelumnya.
- **TanStack Query untuk data server, Zustand untuk state klien.** Data API tidak pernah
  disimpan di Zustand.
- Form: react-hook-form + zod. Pesan validasi Bahasa Indonesia di skema.
- Setiap layar menangani 4 keadaan: memuat, kosong, galat, berhasil.
- Sasaran sentuh ≥ 44 px, teks dasar ≥ 16 px, kontras ≥ 4,5:1.
- `components/` tidak boleh mengimpor dari `features/`.
- **Dilarang:** `alert()`, `confirm()`, `prompt()`, `any`, `@ts-ignore`.

## Pengujian

- Uji aturan bisnis ditulis **sebelum** kodenya.
- PostgreSQL sungguhan untuk uji, **bukan SQLite** — separuh aturan hidup di trigger dan RLS.
- Matriks RBAC endpoint × 7 peran. Endpoint baru tanpa baris di matriks → CI gagal.
- Daftar regresi wajib di `docs/07-RENCANA-PENGUJIAN.md` §3 harus tetap hijau.
- Perintah: `ruff check`, `mypy`, `pytest` · `npm run lint`, `npm run typecheck`,
  `npm test` · `flutter analyze`, `flutter test`.

## Alur kerja per iterasi

**ATURAN WAJIB GIT FLOW (Untuk AI & Developer):**
- **DILARANG** melakukan commit atau push langsung ke branch `prod` atau `main`.
- **SELALU** kerjakan tugas di branch `development` atau branch fitur (misal: `feature/nama-fitur`).
- Penggabungan ke `prod` hanya boleh dilakukan melalui proses *Pull Request* yang ditinjau.

1. Pastikan Anda berada di branch `development` atau branch fitur, bukan `prod`.
2. Ambil task berikutnya dari `docs/06-RENCANA-FASE.md`.
3. Baca standar yang relevan.
4. Tulis uji lebih dulu.
5. Kerjakan.
6. Lint + tipe + uji hijau.
7. Regresi wajib masih hijau.
8. Ambiguitas yang diputuskan sendiri → catat di `docs/10-...md` Bagian C.
9. Tandai selesai hanya bila DoD fase terpenuhi.

Satu task per iterasi.

## Jangan

- Mengubah apa pun di `prototype/`.
- Menulis aturan bisnis di router atau di frontend.
- Menambah pustaka UI atau pengelola state kedua.
- Mengompresi PDF atau berkas Office. Hanya foto yang dikompresi.
- Menyimpan rahasia di Git.
- Menyalin data karyawan asli ke staging atau ke komputer developer.
- Menebak saat spesifikasi ambigu — catat di `docs/10-...md` Bagian C.
- Mengirim data pribadi, koordinat, atau jejak tumpukan ke Discord (`docs/17`).
- Membuka port 22 ke internet.
- Menambah fitur di luar MVP. Daftar lanjutan ada di `docs/10-...md` Bagian F.

## Bila ada pertentangan

Instruksi pemilik produk → `docs/02` dan `docs/10` → `prototype/js/domain.js` → `db/` →
dokumen standar → dokumen lain.
```
